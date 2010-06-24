import unittest
import customize.choices

class TestChoicesFileParsingFunctions(unittest.TestCase):
    def test_get(self):
        c = customize.choices.ChoicesFile() # no file loaded
        c.load_choices(simple_choices_file)
        self.assertEqual(c.get('NO_SUCH'), '')
        self.assertEqual(c.get(''), c.choices)
        self.assertEqual(c.get('language'), 'Simple')
        self.assertEqual(c.get('iso-code'), 'smp')
        self.assertEqual(c.get('verb1_name'), 'testverb')
        self.assertEqual(c.get('verb2_name'), 'testverb2')
        self.assertEqual(c.get('verb1_stem1_orth'), 'test')
        self.assertEqual(c.get('verb1_stem1_pred'), 'test_v_1_rel')
        self.assertEqual(c.get('verb2_stem1_orth'), 'test')
        self.assertEqual(c.get('verb2_stem1_pred'), 'test_v_2_rel')
        self.assertEqual(c.get('verb2'),
                {'name':'testverb2', 'valence':'trans',
                    'stem':[{'orth':'test','pred':'test_v_2_rel'}]})

    def test_set(self):
        c = customize.choices.ChoicesFile() # no file loaded
        self.assertEqual(c.choices, {})
        c['abc'] = 5
        self.assertEqual(c.choices, {'abc':5})
        c['def2_ghi'] = 2
        self.assertEqual(c.choices, {'abc':5, 'def':[{}, {'ghi':2}]})
        c['def1_ghi'] = 1
        self.assertEqual(c.choices, {'abc':5, 'def':[{'ghi':1}, {'ghi':2}]})
        c = customize.choices.ChoicesFile() # no file loaded
        c['rst_uvw'] = 2
        self.assertEqual(c.choices, {'rst_uvw': 2})

    def test_del(self):
        c = customize.choices.ChoicesFile() # no file loaded
        c['abc'] = 5
        self.assertEqual(c.choices, {'abc':5})
        del c['abc']
        self.assertEqual(c.choices, {})
        c['abc1_def'] = 1
        c['abc2_def'] = 2
        c['abc2_ghi'] = 3
        self.assertEqual(c.choices, {'abc':[{'def':1},{'def':2,'ghi':3}]})
        del c['abc2_def']
        self.assertEqual(c.choices, {'abc':[{'def':1},{'ghi':3}]})
        del c['abc2']
        self.assertEqual(c.choices, {'abc':[{'def':1},{}]})
        c['abc2_def'] = 2
        c['abc3_def'] = 3
        self.assertEqual(c.choices, {'abc':[{'def':1},{'def':2},{'def':3}]})
        del c['abc2']
        self.assertEqual(c.choices, {'abc':[{'def':1},{},{'def':3}]})
        del c['abc']
        self.assertEqual(c.choices, {})

    def test_delete(self):
        c = customize.choices.ChoicesFile() # no file loaded
        c['abc1_def'] = 5
        self.assertEqual(c.choices, {'abc':[{'def':5}]})
        c.delete('abc1_def', prune=False)
        self.assertEqual(c.choices, {'abc':[{}]})
        c['abc1_def'] = 5
        c.delete('abc1_def', prune=True)
        self.assertEqual(c.choices, {})
        c['abc1_def'] = 5
        c['abc2_def'] = 6
        c.delete('abc1_def', prune=True)
        self.assertEqual(c.choices, {'abc':[{'def':6}]})
        c['abc1_def'] = 5
        c['abc1_ghi'] = 6
        c['abc2_ghi'] = 7
        c.delete('abc1', prune=False)
        self.assertEqual(c.choices, {'abc':[{},{'ghi':7}]})
        c['abc1_def'] = 5
        c['abc1_ghi'] = 6
        c['abc2_ghi'] = 7
        c.delete('abc1', prune=True)
        self.assertEqual(c.choices, {'abc':[{'ghi':7}]})
        c['abc1_def'] = 5
        c['abc1_ghi'] = 6
        c['abc2_ghi'] = 7
        c.delete('abc', prune=True)
        self.assertEqual(c.choices, {})

    def test_split_variable_key(self):
        c = customize.choices.ChoicesFile() # no file loaded
        self.assertEqual(c.split_variable_key(''), [])
        self.assertEqual(c.split_variable_key('abc'),
                         ['abc'])
        self.assertEqual(c.split_variable_key('abc_def'),
                         ['abc_def'])
        self.assertEqual(c.split_variable_key('ab-c_d3ef'),
                         ['ab-c_d3ef'])
        self.assertEqual(c.split_variable_key('abc_def1_ghi'),
                         ['abc_def', '1', 'ghi'])
        self.assertEqual(c.split_variable_key('abc_def1'),
                         ['abc_def', '1'])
        self.assertEqual(c.split_variable_key('abc32_def1_ghi'),
                         ['abc', '32', 'def', '1', 'ghi'])

    def test_parse_choices(self):
        c = customize.choices.ChoicesFile() # no file loaded
        self.assertEqual(c.parse_choices([]), {})
        self.assertEqual(c.parse_choices(['abc=ABC', 'def=DEF']),
                         {'abc': 'ABC', 'def': 'DEF'})
        self.assertEqual(c.parse_choices(['abc1_def=DEF', 'abc1_ghi=GHI']),
                         {'abc': [{'def': 'DEF', 'ghi': 'GHI'}]})
        self.assertEqual(c.parse_choices(['abc1_def=DEF1', 'abc2_def=DEF2']),
                         {'abc': [{'def':'DEF1'}, {'def':'DEF2'}]})
        self.assertEqual(c.parse_choices(['abc2_def=DEF2', 'abc1_def=DEF1']),
                         {'abc': [{'def':'DEF1'}, {'def':'DEF2'}]})
        self.assertRaises(customize.choices.ChoicesFileParseError,
                          c.parse_choices, ['abc2_def=DEF2', 'abc2_def=DEF1'])

    def test_full_key(self):
        c = customize.choices.ChoicesFile()
        self.assertEqual(c.choices.full_key, None)
        c['abc1_def'] = 1
        c['abc2_def'] = 2
        self.assertEqual(c['abc'].full_key, 'abc')
        for i, key in enumerate(c['abc']):
            self.assertEqual(key.full_key, 'abc' + str(i+1))

    def test_reset_full_keys(self):
        c = customize.choices.ChoicesFile()
        c['abc1_def'] = 1
        c['abc2_def'] = 2
        self.assertEqual(c['abc1'].full_key, 'abc1')
        self.assertEqual(c['abc1_def'], 1)
        self.assertEqual(c['abc2'].full_key, 'abc2')
        self.assertEqual(c['abc2_def'], 2)
        c.delete('abc1', prune=True)
        self.assertEqual(c['abc1'].full_key, 'abc1')
        self.assertEqual(c['abc1_def'], 2)
        c['abc1_def'] = 1
        c['abc2_def'] = 2
        c['abc3_def'] = 3
        c['abc4_def'] = 4
        c.delete('abc2', prune=True)
        self.assertEqual(c['abc1_def'], 1)
        self.assertEqual(c['abc2_def'], 3)
        self.assertEqual(c['abc3_def'], 4)
        c['abc1_def'] = 1
        c['abc2_def'] = 2
        c['abc2_ghi1_klm'] = 3
        c['abc2_ghi2_klm'] = 4
        c.delete('abc1', prune=True)
        self.assertEqual(c['abc1_def'], 2)
        self.assertEqual(c['abc1_ghi1_klm'], 3)
        self.assertEqual(c['abc1_ghi2_klm'], 4)

    # The following functionality is not included. There are difficulties
    # with resetting values that prevent its feasibility at this time, such
    # as "what if they named their language 'abc2'?".
    #
    #def test_reset_full_keys_and_values(self):
    #    c = customize.choices.ChoicesFile()
    #    c['abc1_def'] = 1
    #    c['abc2_def'] = 2
    #    c['abc3_def'] = 'abc2'
    #    self.assertEqual(c['abc3_def'], 'abc2')
    #    c.delete('abc1', prune=True)
    #    self.assertEqual(c['abc1_def'], 2)
    #    self.assertEqual(c['abc2_def'], 'abc1')
    #    c = customize.choices.ChoicesFile()
    #    c['abc1_def'] = 1
    #    c['abc2_def'] = 'abc1' # will be removed
    #    c['abc3_def'] = 'abc2'
    #    c['abc4_def'] = 'abc2' # distance more than 1
    #    c['ghi'] = 'abc2'      # different key
    #    c.delete('abc1', prune=True)
    #    self.assertEqual(c['abc1_def'], None)
    #    self.assertEqual(c['abc2_def'], 'abc1')
    #    self.assertEqual(c['abc3_def'], 'abc1')
    #    self.assertEqual(c['ghi'], 'abc1')

class TestChoicesDerivedValueFunctions(unittest.TestCase):
    def setUp(self):
        self.c = customize.choices.ChoicesFile()

    def test_has_case(self):
        feat = {'name':'case', 'value':'abc'}
        self.assertTrue(self.c.has_case(feat, 'abc'))
        self.assertTrue(self.c.has_case(feat, ''))
        self.assertFalse(self.c.has_case(feat, 'def'))

    def test_has_noun_case(self):
        pass
    def test_has_adp_case(self):
        pass
    def test_has_optadp_case(self):
        pass
    def test_has_mixed_case(self):
        pass
    def test_case_head(self):
        pass
    def test_has_dirinv(self):
        pass
    def test_has_SCARGS(self):
        pass
    def test_cases(self):
        pass
    def test_patterns(self):
        pass

    def test_numbers(self):
        c = customize.choices.ChoicesFile()
        # no numbers section
        c.load_choices(minimal_choices_file)
        self.assertEqual(c.numbers(), [])
        # empty numbers section
        c.load_choices(simple_choices_file)
        self.assertEqual(c.numbers(), [])
        # simple number system
        c.load_choices(mini_english_choices_file)
        self.assertEqual(c.numbers(), [['sg','number'],['pl','number']])
        # delete one
        c.delete('number1')
        self.assertEqual(c.numbers(), [['pl','number']])
        # number hierarchy
        c.load_choices(modified_english_choices_file)
        self.assertEqual(c.numbers(), [['sg','number'],['pl','number'],
                                       ['du','sg;pl']])

    def test_persons(self):
        pass
    def test_pernums(self):
        pass
    def test_genders(self):
        pass
    def test_forms(self):
        pass
    def test_tenses(self):
        pass
    def test_aspects(self):
        pass
    def test_situations(self):
        pass
    def test_types(self):
        pass
    def test_features(self):
        pass

class TestExampleChoicesFiles(unittest.TestCase):
    def setUp(self):
#        self.ch = customize.choices.ChoicesFile()
        pass

##############################################################################
#### Choices File Strings

empty_choices_file = ['']

minimal_choices_file = '''version=18

section=general
language=Minimal
archive=no'''.splitlines()

simple_choices_file = '''version=18

section=general
language=Simple
iso-code=smp
archive=no

section=word-order
word-order=free
has-dets=no
has-aux=no

section=number

section=person
person=none

section=gender

section=case
case-marking=none

section=direct-inverse

section=tense-aspect

section=other-features

section=sentential-negation

section=coordination

section=matrix-yes-no

section=arg-opt

section=lexicon
  noun1_name=testnoun
  noun1_det=imp
    noun1_stem1_orth=test
    noun1_stem1_pred=test_n_1_rel
  verb1_name=testverb
  verb1_valence=intrans
    verb1_stem1_orth=test
    verb1_stem1_pred=test_v_1_rel
  verb2_name=testverb2
  verb2_valence=trans
    verb2_stem1_orth=test
    verb2_stem1_pred=test_v_2_rel

section=test-sentences'''.splitlines()

mini_english_choices_file = '''version=17

section=general
language=mini English
archive=no

section=word-order
word-order=svo
has-dets=yes
noun-det-order=det-noun
has-aux=no

section=number
  number1_name=sg
  number2_name=pl

section=person
person=1-2-3
first-person=none

section=gender

section=case
case-marking=none

section=direct-inverse

section=tense-aspect

section=other-features

section=sentential-negation

section=coordination

section=matrix-yes-no

section=arg-opt

section=lexicon
  noun1_name=common
    noun1_feat1_name=person
    noun1_feat1_value=3rd
  noun1_det=obl
    noun1_stem1_orth=cat
    noun1_stem1_pred=_cat_n_rel
    noun1_stem2_orth=dog
    noun1_stem2_pred=_dog_n_rel
  noun2_name=1sg-pronoun
    noun2_feat1_name=person
    noun2_feat1_value=1st
    noun2_feat2_name=number
    noun2_feat2_value=sg
  noun2_det=imp
    noun2_stem1_orth=I
    noun2_stem1_pred=_pronoun_n_rel
  noun-slot1_name=num
  noun-slot1_order=after
    noun-slot1_input1_type=noun1
    noun-slot1_morph1_name=singular
      noun-slot1_morph1_feat1_name=number
      noun-slot1_morph1_feat1_value=sg
    noun-slot1_morph2_name=plural
    noun-slot1_morph2_orth=s
      noun-slot1_morph2_feat1_name=number
      noun-slot1_morph2_feat1_value=pl
  verb1_name=itr
  verb1_valence=intrans
    verb1_stem1_orth=sleep
    verb1_stem1_pred=_sleep_v_rel
  verb2_name=tr
  verb2_valence=trans
    verb2_stem1_orth=chase
    verb2_stem1_pred=_chase_v_rel
  verb-slot1_name=pernum
  verb-slot1_order=after
    verb-slot1_input1_type=verb
    verb-slot1_morph1_name=3sg
    verb-slot1_morph1_orth=s
      verb-slot1_morph1_feat1_name=person
      verb-slot1_morph1_feat1_value=3rd
      verb-slot1_morph1_feat1_head=subj
      verb-slot1_morph1_feat2_name=number
      verb-slot1_morph1_feat2_value=sg
      verb-slot1_morph1_feat2_head=subj
    verb-slot1_morph2_name=pl
      verb-slot1_morph2_feat1_name=number
      verb-slot1_morph2_feat1_value=pl
      verb-slot1_morph2_feat1_head=subj
    verb-slot1_morph3_name=non-3rd
      verb-slot1_morph3_feat1_name=person
      verb-slot1_morph3_feat1_value=1st, 2nd
      verb-slot1_morph3_feat1_head=subj
    det1_stem1_orth=the
    det1_stem1_pred=_def_q_rel

section=test-sentences
sentence1=the cat chases the dog
sentence2=the dogs sleep'''.splitlines()

modified_english_choices_file = '''version=17

section=general
language=mini English
archive=no

section=word-order
word-order=svo
has-dets=yes
noun-det-order=det-noun
has-aux=no

section=number
  number1_name=sg
  number2_name=pl
  number3_name=du
  number3_supertype1_name=sg
  number3_supertype2_name=pl

section=person
person=1-2-3
first-person=none

section=gender

section=case
case-marking=none

section=direct-inverse

section=tense-aspect

section=other-features

section=sentential-negation

section=coordination

section=matrix-yes-no

section=arg-opt

section=lexicon
  noun1_name=common
    noun1_feat1_name=person
    noun1_feat1_value=3rd
  noun1_det=obl
    noun1_stem1_orth=cat
    noun1_stem1_pred=_cat_n_rel
    noun1_stem2_orth=dog
    noun1_stem2_pred=_dog_n_rel
  noun2_name=1sg-pronoun
    noun2_feat1_name=person
    noun2_feat1_value=1st
    noun2_feat2_name=number
    noun2_feat2_value=sg
  noun2_det=imp
    noun2_stem1_orth=I
    noun2_stem1_pred=_pronoun_n_rel
  noun-slot1_name=num
  noun-slot1_order=after
    noun-slot1_input1_type=noun1
    noun-slot1_morph1_name=singular
      noun-slot1_morph1_feat1_name=number
      noun-slot1_morph1_feat1_value=sg
    noun-slot1_morph2_name=plural
    noun-slot1_morph2_orth=s
      noun-slot1_morph2_feat1_name=number
      noun-slot1_morph2_feat1_value=pl
  verb1_name=itr
  verb1_valence=intrans
    verb1_stem1_orth=sleep
    verb1_stem1_pred=_sleep_v_rel
  verb2_name=tr
  verb2_valence=trans
    verb2_stem1_orth=chase
    verb2_stem1_pred=_chase_v_rel
  verb-slot1_name=pernum
  verb-slot1_order=after
    verb-slot1_input1_type=verb
    verb-slot1_morph1_name=3sg
    verb-slot1_morph1_orth=s
      verb-slot1_morph1_feat1_name=person
      verb-slot1_morph1_feat1_value=3rd
      verb-slot1_morph1_feat1_head=subj
      verb-slot1_morph1_feat2_name=number
      verb-slot1_morph1_feat2_value=sg
      verb-slot1_morph1_feat2_head=subj
    verb-slot1_morph2_name=pl
      verb-slot1_morph2_feat1_name=number
      verb-slot1_morph2_feat1_value=pl
      verb-slot1_morph2_feat1_head=subj
    verb-slot1_morph3_name=non-3rd
      verb-slot1_morph3_feat1_name=person
      verb-slot1_morph3_feat1_value=1st, 2nd
      verb-slot1_morph3_feat1_head=subj
    det1_stem1_orth=the
    det1_stem1_pred=_def_q_rel

section=test-sentences
sentence1=the cat chases the dog
sentence2=the dogs sleep'''.splitlines()
if __name__ == '__main__':
    unittest.main()
