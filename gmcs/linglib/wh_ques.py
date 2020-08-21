'''
Module to support the Constituent (Wh-) Questions library.
email olzama@uw.edu with both constituent and polar questions about the library.
'''

from gmcs.utils import get_name,TDLencode, orth_encode

from gmcs import globals


'''
CONSTANTS
'''

WH_Q_PHR_NO_OR_SG_OBLIG_MULTI = ''' wh-ques-phrase := 
   [ SYNSEM.NON-LOCAL.QUE #que,
     HEAD-DTR.SYNSEM.NON-LOCAL.QUE #que ].'''

WH_Q_PHR = ''' wh-ques-phrase := basic-head-filler-phrase & interrogative-clause &
		  head-final &
   [ SYNSEM [ LOCAL.CAT [ WH.LOGICAL-OR.BOOL +, MC bool,
			VAL #val,
			HEAD verb ], NON-LOCAL.QUE 0-alist ],
     HEAD-DTR.SYNSEM [ LOCAL.CAT [ VAL #val & [ SUBJ < >,
					      COMPS < > ] ] ],
     NON-HEAD-DTR.SYNSEM [ NON-LOCAL.QUE.LIST < ref-ind >,
                           LOCAL.CONT.HOOK.ICONS-KEY focus ] ].'''


MAIN_WHQ = '''main-wh-ques-phrase := wh-ques-phrase &
  [ HEAD-DTR.SYNSEM.LOCAL.CAT.MC na-or-+,
    SYNSEM.LOCAL.CAT.MC + ].
'''

EMBED_WHQ = '''embed-wh-ques-phrase := wh-ques-phrase &
  [ HEAD-DTR.SYNSEM.LOCAL.CAT.MC -,
    SYNSEM.LOCAL.CAT.MC - ].'''

EX_COMP = ''' extracted-comp-phrase := basic-extracted-comp-phrase.'''

EX_SUBJ = ''' extracted-subj-phrase := basic-extracted-subj-phrase &
  [ SYNSEM.LOCAL.CAT.HEAD verb ].'''

IN_SITU_PHRASE = '''insitu-int-cl := interrogative-clause & head-only &
  [ SYNSEM [ MODIFIED hasmod,
             LOCAL.CAT [ VAL #val,
       MC bool ],
       NON-LOCAL [ SLASH.LIST < >, QUE.LIST < >, REL.LIST < >, YNQ #ynq ] ],
    C-CONT [ RELS.LIST < >,
       HCONS.LIST < > ],
    HEAD-DTR.SYNSEM [ LOCAL.CAT [ HEAD verb,
          VAL #val & 
            [ SUBJ < >,
              COMPS < > ] ],
          NON-LOCAL [ SLASH.LIST < >,
          REL.LIST < >,
          QUE.LIST < ref-ind, ... >, YNQ #ynq ] ] ].'''

EX_DET_PHRASE = '''extracted-det-phrase := basic-extracted-arg-phrase & head-compositional &
[ SYNSEM [ LOCAL.CAT [ VAL [ SUBJ < >, COMPS < >, SPR < >, SPEC < > ] ] ],
  HEAD-DTR.SYNSEM [ MODIFIED notmod,
                    LOCAL.CAT.VAL.SPR <  gap & [ LOCAL #local & local &
                                                [ CAT.HEAD det,
                                                  CONT.HOOK #hook ] ] >,
                   L-PERIPH -,
                   NON-LOCAL.SLASH.LIST < #local > ],
    C-CONT [ RELS.LIST < >,
             HCONS.LIST < >,
             ICONS.LIST < >,
             HOOK #hook ] ].'''

BASIC_FILLER_SG = '''basic-filler-phrase :+ [ SYNSEM.NON-LOCAL.SLASH.LIST < >,
                                           ARGS < [ SYNSEM [ LOCAL #slash,
                                                             NON-LOCAL.SLASH.LIST < > ] ], 
                                                    [ SYNSEM.NON-LOCAL.SLASH.LIST < #slash > ] > ]. '''

FIRST_FILLER = '''1st-head-filler-phrase := basic-filler-phrase & head-compositional &
  [  SYNSEM [ NON-LOCAL [ SLASH.LIST #slash, REL #rel, QUE 0-alist, YNQ 0-alist ] ],
     ARGS < [ SYNSEM.LOCAL #local & [ CAT.HEAD +nrpd ] ],
	   [ SYNSEM.NON-LOCAL [ SLASH.LIST < #local . #slash >,
				                  REL #rel & 0-alist ] ] > ].'''

SEC_FILLER = '''2nd-head-filler-phrase := binary-phrase & phrasal & head-compositional &
  [ SYNSEM.NON-LOCAL.SLASH.LIST < #firstarg . #otherargs >,
    ARGS < [ SYNSEM.LOCAL #local ],
     [ SYNSEM.NON-LOCAL [ SLASH.LIST [ FIRST #firstarg, REST < #local . #otherargs > ],
          REL 0-alist ] ] > ].'''

NC_SUBJ_HEAD = '''
subj-head-nc-phrase := decl-head-subj-phrase & head-final &
  [ SYNSEM.LOCAL.CAT [ MC - ],
    HEAD-DTR.SYNSEM.LOCAL.CAT.VAL [ COMPS < > ] ].

'''

from gmcs.constants import MTRX_FR_OPT, MTRX_FRONT, NO_MULTI, \
    SINGLE, MULTI, SG_OBLIG, ALL_OBLIG, EMB_INSITU, ON, WH_INFL, \
    IN_SITU


# This function should be finished when/if WH feature is moved from matrix.tdl to customization
def customize_wh_feature(mylang,ch):
    mylang.add('cat :+ [ WH and-or ].')
    if ch.get(MTRX_FRONT):
        mylang.add('wh-ques-phrase := [ SYNSEM.LOCAL.CAT.WH.LOGICAL-OR.BOOL + ].')
        if len(ch.get('adv', [])) > 0 or len(ch.get('normadp', [])) > 0:
            mylang.add('norm-adposition-lex := [ SYNSEM.LOCAL.CAT.WH or-and-plus ].')



def customize_wh_ques(mylang,ch,rules,roots):
    if (not ch.get(MTRX_FRONT)) and ch.get(WH_INFL) != 'on':
        # If there are no wh-questions, need to put the default
        # constraints to establish the semantic links between
        # the filler and the gap and the extracted subject and the verb:
        mylang.add(BASIC_FILLER_SG,section='phrases')
        mylang.add(EX_SUBJ,section='phrases')
        mylang.add('''clause :+ [ SYNSEM.NON-LOCAL.QUE 0-alist ]. ''')
    else:
        if ch.get('person') == '1-2-3':
            mylang.add('wh-pronoun-noun-lex := [ SYNSEM.LOCAL.CONT.HOOK.INDEX.PNG.PER 3rd ].')

    # Either no fronting at all or single fronting
    if (not ch.get(MTRX_FRONT)) or ch.get(MTRX_FRONT) == SINGLE:
        if len(ch.get('adv', [])) > 0 or len(ch.get('normadp', [])) > 0:
            if ch.get(NO_MULTI) != ON and not ch.get('wh-q-inter-verbs'):
                mylang.add('''head-adj-int-phrase :+ [ HEAD-DTR.SYNSEM [ L-QUE -,
                                LOCAL.CAT.VAL [ SUBJ clist, COMPS clist ] ] ].''',section='addenda')
            mylang.add('''adj-head-int-phrase :+ [ HEAD-DTR.SYNSEM.NON-LOCAL.SLASH 0-alist ].''',section='addenda')

    if (not ch.get(MTRX_FRONT) and ch.get(WH_INFL) != ON) :
        mylang.add('''clause :+ [ SYNSEM.NON-LOCAL.QUE.LIST < > ]. ''')
        if len(ch.get('adv', [])) > 0 or len(ch.get('normadp', [])) > 0:
            mylang.add('''head-adj-int-phrase :+ [ NON-HEAD-DTR.SYNSEM.NON-LOCAL.QUE.LIST < > ]. ''',section='addenda')

    if ch.get(NO_MULTI) == ON:
        mylang.add('''clause :+ [ SYNSEM.NON-LOCAL.QUE 0-1-alist ]. ''')
        if ch.get(MTRX_FRONT) in [SINGLE]:
            mylang.add('''wh-ques-phrase := [ HEAD-DTR.SYNSEM.NON-LOCAL.QUE 0-alist ].''')
        if len(ch.get('adv', [])) > 0 or len(ch.get('normadp', [])) > 0:
            mylang.add('''wh-adverb-lex := [ SYNSEM.LOCAL.CAT.HEAD.MOD < [ LOCAL.CAT.WH.LOGICAL-OR.BOOL - ] > ].''')

    mylang.add_literal(';;; Wh-question-related phrasal types',section='phrases')

    if ch.get(MTRX_FRONT) in [SINGLE, MULTI]:
        mylang.add_literal('''; Do not allow extracting "And Kim"''')
        mylang.add('''basic-head-filler-phrase :+
   [ ARGS < [ SYNSEM.LOCAL.COORD - ], [ SYNSEM.LOCAL.COORD - ] > ].''')
        mylang.add(WH_Q_PHR,section='phrases')
        if not ch.get('wh-inv-matrix') == ON:
            mylang.add('wh-ques-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.MC na-or-+ ].')
        else:
            if not ch.get('wh-inv-embed') == ON:
                mylang.add(MAIN_WHQ)
                mylang.add(EMBED_WHQ)
            else:
                mylang.add('wh-ques-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.MC na-or-+ ].')
        mylang.add_literal('; Complement extraction',section='phrases')
        mylang.add(EX_COMP)
        rules.add('ex-comp := extracted-comp-phrase.')
        mylang.add_literal('; Adjunct extraction',section='phrases')
        if ch.get(MTRX_FRONT) == MULTI:
            rules.add('ex-adj-last := extracted-adj-last-phrase.')
        rules.add('ex-adj-first := extracted-adj-first-phrase.')
        # Free probably shouldn't belong here? check
        if ch.get('word-order') in ['vos','svo','sov','free']:
            if ch.get('pied-pip-adp') != 'on' or ch.get('oblig-pied-pip-adp') == ON:
                mylang.add('extracted-comp-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ cons ].',merge=True)
            mylang.add('extracted-subj-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS < > ].',merge=True)
        elif ch.get('word-order') in ['vso','osv','ovs']:
            mylang.add('extracted-comp-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ < > ].',merge=True)



    if ch.get(MTRX_FRONT) in [SINGLE]:
        # With single fronting, can restrict SLASH to one element at most
        mylang.add(BASIC_FILLER_SG,section='phrases')
        mylang.add_literal('; Subject extraction')
        mylang.add(EX_SUBJ)
        rules.add('ex-subj := extracted-subj-phrase.')
        if not ch.get('wh-inv-matrix') == ON:
            rules.add('wh-ques := wh-ques-phrase.')
        else:
            if not ch.get('wh-inv-embed') == ON:
                rules.add('main-whq := main-wh-ques-phrase.')
                rules.add('embed-whq := embed-wh-ques-phrase.')
            else:
                rules.add('wh-ques := wh-ques-phrase.')

        if ch.get(MTRX_FR_OPT) == SG_OBLIG:
            mylang.add('''head-adj-int-phrase :+ [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL [ SUBJ clist, COMPS clist ] ].''')

        if ch.get('wh-inv-matrix') == ON:
            if not ch.get('wh-inv-notsubj') == ON:
                mylang.add('wh-ques-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD.AUX + ].')
            else:
                mylang.add('extracted-subj-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD.AUX - ].')
            if not ch.get('wh-inv-embed') == ON:
                mylang.add('subj-head-phrase := [ SYNSEM.LOCAL.CAT.MC na-or-+,'
                       'HEAD-DTR.SYNSEM.NON-LOCAL [ QUE.LIST < >, SLASH.LIST < > ] ].')
                mylang.add('adj-head-int-phrase :+ [ NON-HEAD-DTR.SYNSEM.NON-LOCAL [ QUE.LIST < > ] ].')
                mylang.add(NC_SUBJ_HEAD, section='phrases')
                rules.add('nc-subjh := subj-head-nc-phrase.')
            mylang.add('extracted-adj-first-phrase :+ '
                       '[ SYNSEM.NON-LOCAL.SLASH.LIST < [ CAT.HEAD.MOD < [ LOCAL.CAT.HEAD [ INV - ] ] > ] >, '
                       '  HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS < > ].')


    if ch.get(MTRX_FRONT) in [MULTI]:
        mylang.add(EX_SUBJ, section='phrases')
        mylang.add('extracted-subj-phrase := [ HEAD-DTR.SYNSEM.L-QUE - ].')
        rules.add('ex-subj := extracted-subj-phrase.')
        mylang.add('wh-ques-phrase := [ HEAD-DTR.SYNSEM.NON-LOCAL.SLASH.LIST < [], ... > ].')
        mylang.add(FIRST_FILLER)
        # prevent adjunct extraction, as it will be done out of head-subj
        if ch.get(MTRX_FR_OPT) == 'none-oblig':
            mylang.add('1st-head-filler-phrase := [ SYNSEM.MODIFIED hasmod ].')
        mylang.add('wh-ques-phrase := 1st-head-filler-phrase.')
        rules.add('wh-ques := wh-ques-phrase.')
        if ch.get(MTRX_FR_OPT) == ALL_OBLIG:
            mylang.add(WH_Q_PHR_NO_OR_SG_OBLIG_MULTI) # QUE.LIST is empty
        # Rule out structural ambiguity for sentences like "Who sleeps where?"
        if ch.get('word-order') in ['svo', 'sov', 'osv' ]:
            mylang.add('''head-adj-int-phrase :+ [ HEAD-DTR.SYNSEM [ L-QUE -,
             LOCAL.CAT.VAL [ SUBJ clist, COMPS clist ] ] ].''',section='addenda')
        if ch.get('word-order') == 'free':
            mylang.add('''adj-head-int-phrase :+ [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ clist ].''', merge=True)
            mylang.add('''head-adj-int-phrase :+ [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ clist ].''', merge=True)
        # The below does not make sense?
        if ch.get('word-order') in ['ovs', 'vos', 'vso']:
            mylang.add('''adj-head-int-phrase :+ [ HEAD-DTR.SYNSEM.L-QUE - ].''',section='addenda')

    if (ch.get(MTRX_FRONT) in [SINGLE] and ch.get(MTRX_FR_OPT) == 'none-oblig'):
        if ch.get('word-order') in ['ovs', 'vos', 'vso']:
            mylang.add('''adj-head-int-phrase :+ [ NON-HEAD-DTR.SYNSEM.L-QUE - ].''',section='addenda')

    # If fronting is optional, need to use the peripheral feature to rule out ambiguity.
    if (ch.get(MTRX_FRONT) == SINGLE) \
            or (ch.get(MTRX_FRONT) == MULTI and not ch.get(MTRX_FR_OPT) == ALL_OBLIG):
        mylang.add('phrase-or-lexrule :+ [ SYNSEM.L-QUE #lque, ARGS.FIRST.SYNSEM.L-QUE #lque ].')

    # If the fronting isn't obligatory or if only one question phrase
    # is obligatorily fronted, need also in-situ rules:
    if (ch.get(MTRX_FRONT) == SINGLE and not ch.get(MTRX_FR_OPT) == SG_OBLIG) \
            or ch.get(MTRX_FRONT) == IN_SITU \
            or (ch.get(MTRX_FRONT) == MULTI and not ch.get(MTRX_FR_OPT) == ALL_OBLIG) \
            or ch.get(WH_INFL) == ON:
        mylang.add_literal('; In-situ interrogative clause.',section='phrases')
        mylang.add(IN_SITU_PHRASE)
        rules.add('in-situ-ques := insitu-int-cl.')
        if not ch.get(MTRX_FRONT) == IN_SITU:
            if ch.get(EMB_INSITU) == ON:
                mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.WH.LOGICAL-OR.BOOL + ].')
            else:
                mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.WH.LOGICAL-OR.BOOL - ].')
        else:
            mylang.add('''insitu-int-cl := [ SYNSEM.LOCAL.CAT.WH.LOGICAL-OR.BOOL + ].''')
        if ch.get(MTRX_FRONT) in [SINGLE,MULTI]:
            mylang.add('insitu-int-cl := [ SYNSEM.L-QUE - ].')
        if (ch.get(MTRX_FRONT) == SINGLE
            and not ch.get(MTRX_FR_OPT) == SG_OBLIG) \
                and not ch.get(EMB_INSITU) == ON:
            mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.MC + ].')
        elif ch.get(MTRX_FRONT) == 'multi' and ch.get(MTRX_FR_OPT) == SG_OBLIG:
            mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.MC - ].')
        # For non-free word orders, need to rule out structural ambiguity:
        if ch.get('word-order') in ['svo', 'sov'] \
                and not (ch.get(MTRX_FRONT) == IN_SITU
                         or ch.get(WH_INFL) == ON):
            mylang.add('subj-head-phrase := [ NON-HEAD-DTR.SYNSEM.NON-LOCAL.QUE.LIST < > ].')

    # Obligatory pied piping of both nouns and adpositions is the default.
    # If there is no pied piping or it is optional, additional extraction rules are needed.
    if ch.get(MTRX_FRONT) in [SINGLE, MULTI] and len(ch.get('det', [])) > 0:
        if (not ch.get('pied-pip') == ON or (ch.get('pied-pip')==ON
                                               and not (ch.get('oblig-pied-pip-noun')== ON))):
            mylang.add_literal('; If there is no obligatory pied-piping, determiners '
                               'can be extracted separately:',section='phrasal')
            mylang.add(EX_DET_PHRASE,section='phrases')
            if ch.get('case'):
                mylang.add('''extracted-det-phrase :=
                [ SYNSEM.LOCAL.CAT.HEAD.CASE #case,
                HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SPR.FIRST.LOCAL.CAT.VAL.SPEC.FIRST.LOCAL.CAT.HEAD.CASE #case ].''')
            if ch.has_png():
                mylang.add('''extracted-det-phrase :=
                [ SYNSEM.LOCAL.CONT.HOOK.INDEX.PNG #png,
                HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SPR.FIRST.LOCAL.CAT.VAL.SPEC.FIRST.LOCAL.CONT.HOOK.INDEX.PNG #png ].''')
            rules.add('ex-det := extracted-det-phrase.')
        # The following would rule out "Which royal house did you see a member of?"
        #if ch.get('pied-pip-adp') == 'on' and not ch.get('oblig-pied-pip-adp') == ON:
            #mylang.add('extracted-comp-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD +vp ].')
            #if ch.get('word-order') in ['vos', 'vso', 'ovs','v-initial']:
            #mylang.add('head-spec-phrase := [ HEAD-DTR.SYNSEM.NON-LOCAL.SLASH.LIST < > ].')
        #else:
        #    mylang.add('extracted-comp-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD verb ].')

        if ch.get('pied-pip-adp') == ON and \
                ch.get('oblig-pied-pip-noun') != ON \
                and ch.get('oblig-pied-pip-adp') == ON:
            mylang.add('norm-adposition-lex := [ SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.NON-LOCAL.SLASH.LIST < > ].')

    if ch.get('q-part') == ON:
        if ch.get(MTRX_FRONT) == IN_SITU:
            mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.WH.LOGICAL-OR.BOOL + ].')
            # Perhaps this special case below can be dealt with differently?
            # Like with the WH feature?
            if len(ch.get('q-particle')) == 1:
              qpart = ch.get('q-particle')[1] # This is 1 and not 0 because the Choices len method is overriden; see Choices.py
              if qpart['wh'] == 'oblig':
                   mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.MC - ].')
            elif globals.div_particles:
                mylang.add('insitu-int-cl := [ SYNSEM.LOCAL.CAT.MC - ].')