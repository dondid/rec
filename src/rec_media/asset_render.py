"""Versioned scene pixel pipeline for additive asset scenes. Entirely offline."""
from copy import deepcopy
import math
from pathlib import Path
import uuid
from PIL import Image
from . import core
from .content import fit_image, text_layer

PIPELINE = 'scene-assets-v1'


def pixel_scene(scene):
    keys=['kind','fit','focal','crop','zoom','pan','motion','motion_amount','source_start','source_end',
          'short_policy','transition','overlay','title_overlay','subtitle_placement','render_frames','render_padding']
    value={k:deepcopy(scene[k]) for k in keys if k in scene}
    value['asset_checksum']=scene['asset']['sha256']
    return value


def identity(scene, size, config):
    return core.key(dict(pipeline=PIPELINE, pixels=pixel_scene(scene), size=size, config=config,
                         implementation=core.sha(__file__), content=core.sha(Path(__file__).with_name('content.py')),
                         ffmpeg=core.sha(core.tool('ffmpeg')),font=core.sha(config['font'])))


def generate(document, scene, size, config, folder, destination, frames, padding):
    asset=core.checked(document,scene['asset']);fps=config['fps'];w,h=size
    fit=scene.get('fit',config['fit']);focal=scene.get('focal',[.5,.5]);motion=scene.get('motion','none')
    crop=scene.get('crop');zoom=scene.get('zoom',1);amount=scene.get('motion_amount',config['motion_amount'])
    if not 0<=amount<=.15:raise ValueError('motion_amount invalid.')
    nonce=uuid.uuid4().hex
    if scene['kind']=='image':
        with Image.open(asset) as original:
            original=original.convert('RGB')
            if crop:original=original.crop(tuple(round(x*y) for x,y in zip(crop,[original.width,original.height]*2)))
            if zoom!=1:
                cw,ch=original.width/zoom,original.height/zoom;x=(original.width-cw)*focal[0];y=(original.height-ch)*focal[1]
                original=original.crop((round(x),round(y),round(x+cw),round(y+ch)))
            background=fit_image(original,tuple(size),fit,focal)
        image=folder/f'asset-bg-{nonce}.png';background.save(image)
        args=['-threads',str(config['threads']),'-loop','1','-framerate',str(fps),'-i',image]
        vf=f'fps={fps}'
        if motion!='none':vf=motion_filter(motion,amount,focal,scene.get('pan'),frames,size,fps,frames)
    else:
        data=safe_probe(asset);v=next(s for s in data['streams'] if s['codec_type']=='video')
        duration=float(v.get('duration') or data['format']['duration'])
        start=scene.get('source_start',0);end=scene['source_end'] if scene.get('source_end') is not None else duration
        if not 0<=start<end<=duration+.001:raise ValueError('Intervalul video depășește sursa verificată.')
        available=end-start;needed=frames/fps;policy=scene.get('short_policy','error')
        if available+.001<needed and policy=='error':raise ValueError('Clip prea scurt: alege explicit loop/freeze/alt asset/secvență/fallback imagine.')
        # Isolate the requested interval before looping; never loop unrelated source footage.
        segment=folder/f'asset-segment-{nonce}.mkv'
        core.ff(local_inputs(['-threads',str(config['threads']),'-ss',str(start),'-i',asset,'-t',str(available),'-vf',f'fps={fps},setpts=PTS-STARTPTS',
                 '-an','-c:v','ffv1','-threads',str(config['threads']),segment]))
        args=['-threads',str(config['threads'])]
        if policy=='loop' and available<needed:args+=['-stream_loop','-1']
        args+=['-i',segment]
        filters=[]
        if crop:
            a,b,c,d=crop;filters.append(f'crop=iw*{c-a}:ih*{d-b}:iw*{a}:ih*{b}')
        if zoom!=1:filters.append(f'crop=iw/{zoom}:ih/{zoom}:(iw-ow)*{focal[0]}:(ih-oh)*{focal[1]}')
        if fit=='contain':filters.append(f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x14232f')
        else:filters.append(f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-ow)*{focal[0]}:(ih-oh)*{focal[1]}')
        filters.append(f'fps={fps}')
        if policy=='freeze' and available<needed:filters.append(f'tpad=stop_mode=clone:stop_duration={needed-available+1/fps}')
        if motion!='none':filters.append(motion_filter(motion,amount,focal,scene.get('pan'),frames,size,fps,1))
        vf=','.join(filters)
    vf+=f',trim=end_frame={frames},setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop={padding},setsar=1,format=yuv420p'
    texts=[(scene.get('overlay'),'panel'),(scene.get('title_overlay'),'top')]
    active=[(text,position) for text,position in texts if text]
    if active:
        vf+='[base]';label='base';filters=[f'[0:v]{vf}']
        for i,(text,position) in enumerate(active,1):
            layer,_=text_layer(tuple(size),text,config,position);path=folder/f'overlay-{nonce}-{i}.png';layer.save(path)
            args+=['-threads',str(config['threads']),'-loop','1','-framerate','1','-i',path]
            filters.append(f'[{i}:v]format=rgba,fps={fps}[layer{i}];[{label}][layer{i}]overlay=shortest=1[out{i}]');label=f'out{i}'
        return local_inputs([*args,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map',f'[{label}]','-frames:v',str(frames+padding),'-an','-c:v','ffv1','-threads',str(config['threads']),destination])
    return local_inputs([*args,'-vf',vf,'-frames:v',str(frames+padding),'-an','-c:v','ffv1','-threads',str(config['threads']),destination])


def motion_filter(motion, amount, focal, pan, frames, size, fps, d):
    progress=f'on/{max(1,frames-1)}';w,h=size
    zoom={'zoom_in':f'1+{amount}*{progress}','zoom_out':f'1+{amount}-{amount}*{progress}','pan':str(1+amount)}[motion]
    target=pan or ([1,focal[1]] if motion=='pan' else focal)
    x=f'(iw-iw/zoom)*({focal[0]}+({target[0]-focal[0]})*{progress})'
    y=f'(ih-ih/zoom)*({focal[1]}+({target[1]-focal[1]})*{progress})'
    return f"zoompan=z='{zoom}':x='{x}':y='{y}':d={d}:s={w}x{h}:fps={fps}"


def subtitle_positions(path, scenes, rate, size):
    lines=path.read_text().splitlines();result=[]
    for line in lines:
        if line.startswith('Dialogue: '):
            fields=line.split(',',9);h,m,s=fields[1].split(':');t=int(h)*3600+int(m)*60+float(s)
            scene=next((s for s in scenes if s['start']/rate<=t<s['end']/rate),None)
            if scene and scene.get('subtitle_placement')=='top':fields[9]=r'{\an8\pos('+f'{size[0]//2},{round(size[1]*.08)}'+')}' + fields[9]
            line=','.join(fields)
        result.append(line)
    path.write_text('\n'.join(result)+'\n')


def local_inputs(args):
    result=[]
    for value in args:
        if value=='-i':result+=['-protocol_whitelist','file,pipe']
        result.append(value)
    return result


def safe_probe(path):
    import json
    return json.loads(core.run([core.tool('ffprobe'),'-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',Path(path).resolve()]))
