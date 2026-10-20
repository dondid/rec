"""Form descriptions derived from argparse: one supported command inventory."""
import argparse
from pathlib import Path


def parsers(engine):
    if engine=='media':
        from ..cli import parser
    elif engine=='tts':
        from rec_tts.cli import parser
    else:raise ValueError('Motor necunoscut.')
    return parser()


def catalog(engine):
    def walk(p,prefix=(),inherited=(),inherited_groups=()):
        fields=[]; children=[]
        groups=[dict(required=g.required,names=[a.dest for a in g._group_actions]) for g in p._mutually_exclusive_groups]
        for a in p._actions:
            if isinstance(a,argparse._SubParsersAction):children.append(a);continue
            if a.dest=='help':continue
            default=a.default
            if isinstance(default,Path):default=str(default)
            fields.append(dict(name=a.dest,flags=a.option_strings,required=a.required or not a.option_strings,
                kind='bool' if isinstance(a,(argparse._StoreTrueAction,argparse._StoreFalseAction)) else ('path' if a.type is Path else 'number' if a.type in (int,float) else 'text'),
                multiple=a.nargs in ('+','*'),choices=list(a.choices) if a.choices else None,default=default,help=a.help))
        if children:
            return [item for child in children for name,cp in child.choices.items() for item in walk(cp,(*prefix,name),(*inherited,*fields),(*inherited_groups,*groups))]
        disabled = prefix[0] in ('gui','fetch-model')
        return [dict(engine=engine,command=list(prefix),fields=list((*inherited,*fields)),groups=list((*inherited_groups,*groups)),available=not disabled,
                     limitation='Folosește CLI explicit pentru instalare sau pornirea altui server.' if disabled else None)]
    return walk(parsers(engine))


def arguments(engine, command, values):
    if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command) or not isinstance(values,dict):raise ValueError('Cerere structurată invalidă.')
    spec=next((s for s in catalog(engine) if s['command']==command),None)
    if not spec or not spec['available']:raise ValueError('Operație indisponibilă în Studio; CLI rămâne disponibil.')
    names={f['name'] for f in spec['fields']}
    if set(values)-names:raise ValueError('Opțiuni necunoscute.')
    argv=[]
    # Global options must precede the command, as in the CLI.
    globals_={'config','report'} if engine=='media' else {'config'}
    def append(f):
        name=f['name'];v=values.get(name)
        if v is None or v=='':return
        if f['kind']=='bool':
            if type(v) is not bool:raise ValueError('Boolean invalid.')
            if v:argv.append(f['flags'][-1])
            return
        vals=v if f['multiple'] else [v]
        if not isinstance(vals,list) or any(type(x) not in (str,int,float) for x in vals):raise ValueError('Valoare opțiune invalidă.')
        if f['flags']:argv.append(f['flags'][-1])
        argv.extend(str(x) for x in vals)
    for f in spec['fields']:
        if f['name'] in globals_:append(f)
    argv.extend(command)
    for f in spec['fields']:
        if f['name'] not in globals_:append(f)
    try:a=parsers(engine).parse_args(argv)
    except SystemExit as e:raise ValueError('Opțiuni incomplete sau incompatibile; verifică formularul.') from e
    return a,argv,spec
