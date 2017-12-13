import gmcs.tdl
from gmcs.linglib.word_order import customize_major_constituent_order
from gmcs.linglib.morphotactics import all_position_classes
###################################################################
# Atoms of a possessive strategy:
#
# The rule that combines possessor and possessum
#     Sometimes must be added separately
#     Sometimes already there
#
# For each affix:
# Lexical rule type
#
# For each non-affix:
# Lexical entries + rules to attach these words to their heads
#
###################################################################


# PRIMARY FUNCTION
def customize_adnominal_possession(mylang,ch,rules,irules,lexicon):
    # TODO: add POSS feature and POSS.PNG to head feature here.
    for strat in ch.get('poss-strat',[]):
        customize_rules(strat,mylang,ch,rules)
        customize_irules(strat,mylang,ch,irules)
        #customize_lexicon(strat,mylang,ch,lexicon)



# SECONDARY FUNCTIONS
def customize_rules(strat,mylang,ch,rules):
# TODO: deal with free word order
    """
    Adds the necessary phrase rule to combine possessor and possessum
    If rule already exists (head-comp case), then make sure its order is correct.
    """
    phrase_rule=""
    mylang.set_section('phrases')
    # Adds a head-compositional variant of head-spec if possessor = spec
    if strat.get('mod-spec')=='spec':
        phrase_rule="head-spec-hc-phrase"
        # TODO: constrain head-spec-hc so it only applies to poss-phrases.
        mylang.add(phrase_rule + ' :=  basic-head-spec-phrase-super &  [  NON-HEAD-DTR.SYNSEM [ OPT - ],\
    HEAD-DTR.SYNSEM.LOCAL.CONT.HOOK #hook ,\
    C-CONT.HOOK #hook ].')
    # Adds either head-mod or head-comp if possessor = mod
    elif strat.get('mod-spec')=='mod':
        if strat.get('mark-loc')=='possessum-marking':
            phrase_rule="head-comp-poss-phrase"
            # Check if the existing head-comp rule has the correct order; 
            # if not, add a new rule with correct order that only applies to poss-phrases.
            head_comp_order=customize_major_constituent_order(ch.get('word-order'),mylang,ch,rules)['hc']
            if head_comp_order=='head-comp':
                head_comp_order='head-initial'
            else:
                head_comp_order='head-final'
            if head_comp_order!=strat.get('order'):
                # TODO: constrain head-comp-poss-phrase  so it only applies to poss-phrases.
                mylang.add(phrase_rule +'-poss-phrase  := basic-head-comp-phrase &'+strat.get('order')+' ].')
        else:
            phrase_rule="head-mod-poss-phrase"
            mylang.add('head-mod-phrase := basic-head-mod-phrase-simple & head-compositional & \
     [ SYNSEM.LOCAL.CAT.VAL [ SPEC #spec ], \
       HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SPEC #spec].')
    # Adds word order info to the phrase rule (unless it's the head-comps pattern -- it's already been dealt with) 
    if phrase_rule!='head-comp-poss-phrase':
        if strat.get('order')=='possessor-first':
            mylang.add(phrase_rule + ' := head-final.',merge=True)
        else:
            mylang.add(phrase_rule + ' := head-initial.',merge=True)
    # Adds rule to rules.tdl
    rules.add(phrase_rule.replace('-phrase','') + ':= '+phrase_rule+'. ' )




# NOTE: customize_irules doesn't yet deal with situations where one marker is an affix and one isn't:
# NOTE: customize_irules and customize_lex both don't handle agreement yet


def customize_irules(strat,mylang,ch,irules):
    for npc in ch['noun-pc']:
        for lrt in npc['lrt']:
            for f in lrt['feat']:
                if 'possessor' in f['name']:
                    # Added these supertypes to morphotactics.py as well
                    if strat.get('mod-spec')=='spec' or (strat.get('mod-spec')=='mod' and strat.get('mark-loc')=='possessum-marking'):
                        lrt['supertypes'] = ', '.join(lrt['supertypes'].split(', ') + \
                                                          ['val-change-with-ccont-lex-rule'])
                    else:
                        # This rule type doesn't exist in matrix.tdl. Writing to the forum to see if I can add it there, or just to my grammars, or if it's wrong on some other level.
                        lrt['supertypes'] = ', '.join(lrt['supertypes'].split(', ') + \
                                                          ['head-change-with-ccont-lex-rule'])

    for pc in all_position_classes(ch):
        pc_key = pc.full_key
        pc_inputs = pc.get('inputs',[])
        idx = pc['lrt'].next_iter_num() if 'lrt' in pc else 1
        for lrt in pc.get('lrt',[]):
            print lrt
# I don't think I need to add to morphotactics.py
# Imitate valence_change.py to model lex-rules in library. 

"""
def customize_valence_change(mylang, ch, lexicon, rules, irules, lrules):
    rules = LexRuleBuilder()
    for pc in all_position_classes(ch):
        pc_key = pc.full_key
        pc_inputs = pc.get('inputs',[])
        idx = pc['lrt'].next_iter_num() if 'lrt' in pc else 1
        for lrt in pc.get('lrt',[]):
            for vchop in lrt.get('valchg',[]):
                opname = vchop['operation'].lower()
                if opname == 'subj-rem':
                    rules.add('subj-rem-op', subj_rem_op_lex_rule)
                if opname == 'obj-rem':
                    rules.add('obj-rem-op', obj_rem_op_lex_rule)
                if opname == 'obj-add':
                    rules.add('basic-applicative', basic_applicative_lex_rule)
                    position = vchop.get('argpos','').lower()
                    argtype = vchop.get('argtype','').lower()
                    if position == 'pre':
                        rules.add('added-arg-head-type', added_arg_head_lex_rule, 2, argtype)
                        rules.add('added-arg-applicative', added_arg_applicative_lex_rule, 2, 3)
                        rules.add('added-arg-non-local', added_arg_non_local_lex_rule, 2, 3)
                    elif position == 'post':
                        rules.add('added-arg-head-type', added_arg_head_lex_rule, 3, argtype)
                        rules.add('added-arg-applicative', added_arg_applicative_lex_rule, 3, 3)
                        rules.add('added-arg-non-local', added_arg_non_local_lex_rule, 3, 3)
                if opname == 'subj-add':
                    if 'verb' in pc_inputs or 'iverb' in pc_inputs:
                        rules.add('added-arg-non-local', added_arg_non_local_lex_rule, 1, 2)
                    if 'verb' in pc_inputs or 'tverb' in pc_inputs:
                        rules.add('added-arg-non-local', added_arg_non_local_lex_rule, 1, 3)

    rules.generate_tdl(mylang)

class LexRuleBuilder:
    def __init__(self):
        self.rules = set()
    def add(self,rule_name,rulegen,*rulegen_args):
        self.rules.add(FnWrapper(rule_name,rulegen,*rulegen_args))
    def generate_tdl(self,mylang):
        prev_section = mylang.section
        mylang.set_section('lexrules')
        for rule in self.rules:
            mylang.add(rule())
        mylang.set_section(prev_section)


"""



#     Possessor-marker:
#             If the possessor is specifier-like:
#                ADD possessor-lex-rule with SPEC<[possessum]>, carrying poss_rel
#             If the possessor is  modifier-like:
#                ADD possessor-lex-rule with MOD<[possessum]>, carrying poss_rel
#     Possessum-marker:
#        If the possessor is specifier-like:
#             If single-marking:
#                ADD possessum-lex-rule with SPR<[possessor]>, carrying poss_rel
#             If double-marking:
#                ADD possessum-lex-rule with SPR<[possessor]>
#        If the possessum is modifier-like:
#             If single-marking:
#                ADD possessum-lex-rule with COMPS<[possessor]>, carrying poss_rel
#             If double-marking
#                ADD possessum-lex-rule with COMPS<[possessor]>
#                ADD a feature [HEAD.POSS +] to the possessor infl rule.



# TODO: figure out what happens with double marking
# TODO: add in where the poss_rel is

# def customize_lex(mylang,ch,lexicon):
#     IF: either possessor or possessum mark is a separate word, add the correct lexical entry
#     Possessor-marker:
#        If the possessor is specifier-like:
#            ADD possessor-det-lex, with SPR<[possessor]>, SPEC<[possessum]>, carrying poss_rel
#             OR TRY:
#            ADD possessor-adp-lex, with COMPS<[possessor]>,SPEC<possessum]>
#        If the possessor is modifier-like:
#            ADD possessor-adp-lex, with COMPS<[possessor]>, MOD<[possessum]>
#     Possessum-marker:
#        If the possessor is specifier-like:
#             ADD possessum-noun-lex, with COMPS<[possessum]>, SPR<[possessor]>
#        If the possessor is modifier-like:
#             ADD possessum-noun-lex, with COMPS<[possessum][possessor]>






# Not sure making an object from the choices file is really that helpful, 
# but here's one way you could do it if you wanted to:
#
# A strategy object contains:
#
# Primitives from questionnaire:
# (Try not to add too many obscuring layers between choices file and this)
# juxtaposition: boolean (for convenience -- could be encoded in other variables)
# specifier vs. mod
# NOM: bool
# order: head-first or head-final or free
# mark-loc: head, dep, both
# possessor-affix: boolean
# possessor-sep-word: left-attach, right-attach, none
# possessum-affix: boolean
# possessum-sep-word: left-attach, right-attach, none
#
# Deduced properties:
# rule-type: head-spec-hc, head-comps, head-mod
#     DEPENDS ON: spec-like, mark-loc
# add-lex-rules: bool
#     DEPENDS ON: possessor-affix, possessum-affix
# add-lex-entries: bool
#     DEPENDS ON: possessor-sep-word, possessum-sep-word
# add-phrasal-rules: bool
#     DEPENDS ON: order, rule-type (anything but head-comp guarantees a rule add), 
#     [order info from word-order page]
#
# TDL-adding functions:
# Lexical rules.
#     DEPENDS ON: mark-loc, possessor-affix, possessum-affix
#     [Also unsure of how this interfaces with the stuff on Morphology page]
# Lexical entries.
#     DEPENDS ON: mark-loc, possessor-sep-word, possessum-sep-word
# Phrasal rules for attaching possessor and possessum:
#     DEPENDS ON: order, rule-type, [info from word-order lib]





# Choice 1:
# Order of possessor and possessum
#
# Consequence: 
# Depending on the preexistent order of head-spec, head-mod, and head-comps,
# May have to create a specific version of the above that has the appropriate order:
#     Whatever rule is used in this strategy will have to be added and with the right constraints.
# If preexistent order of head-spec, head-mod, and head-comps is already correct,
# Do nothing.


# Choice 2:
# Modifier vs. specifier
#
# Consequence:
# If specifier, always add head-spec-hc.
#     Also, MANY OTHER CHOICES FALL OUT FROM THIS
# If modifier, add either head-mod or leave in head-comp.
#     Also, MANY OTHER CHOICES FALL OUT FROM THIS

# Choice 3:
# Possessor = NOM vs NP
# 
# Consequence:
# If NOM, then require the possessor (in head-mod or head-spec or head-comps)
# to be SPR 1-dlist. 
# If NP, then require the possessor to be SPR olist.

# Choice 4:
# Complicated stuff
