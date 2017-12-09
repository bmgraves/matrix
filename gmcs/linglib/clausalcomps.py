from gmcs.utils import TDLencode
from gmcs.utils import orth_encode
from gmcs.utils import merge_constraints
from gmcs.lib import TDLHierarchy

from gmcs.linglib import features

######################################################################
# Clausal Complements
#   Create the type definitions associated with the user's choices
#   about clasual complements.

######################################################################


def customize_clausalcomps(mylang,ch,lexicon,rules,irules):
    if not 'comps' in ch:
        return None

    add_complementizers_to_lexicon(lexicon,ch)
    add_ctp_to_lexicon(mylang,lexicon)
    add_complementizer_type_to_grammar(mylang,ch,rules)

def add_complementizer_type_to_grammar(mylang,ch,rules):
    mylang.set_section('complex')
    mylang.add('comp-lex-item := raise-sem-lex-item & basic-one-arg &\
      [ SYNSEM.LOCAL.CAT [ HEAD comp &\
                                [ MOD < > ],\
                           VAL [ SPR < >,\
                                 SUBJ < >,\
                                 COMPS < #comps > ] ],\
        ARG-ST < #comps & \
                 [ LOCAL.CAT [ HEAD verb, MC -,\
                               VAL [ SUBJ < >,\
                                     COMPS < > ] ] ] > ].',section='complex')

    for cs in ch.get('comps'):
        id = cs.full_key
        typename = id + '-comp-lex-item'
        mylang.add(typename + ' := comp-lex-item.', section='complex')
        # merge feature information in
        path = 'SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.LOCAL.CAT.HEAD.FORM'
        merge_constraints(choice=cs, mylang=mylang, typename=typename,path=path,key1='feat',key2='name',val='form')
        #if cs['clause-pos-extra'] == 'on':
        #    pass


def add_complementizers_to_lexicon(lexicon,ch):
    lexicon.add_literal(';;; Complementizers')
    for comp_strategy in ch['comps']:
        for complementizer in comp_strategy['complementizer']:
            orth = complementizer['orth']
            typedef = complementizer.full_key + ' := comp-lex-item & \
                          [ STEM < "' + orth + '" > ].'

            lexicon.add(typedef)

def add_ctp_to_lexicon(mylang,lexicon):
    pass

def add_arg_structures(mylang, ch, lexicon):
    for ccs in ch.get('comps'):
        pass