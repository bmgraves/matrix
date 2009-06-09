### $Id: customize.py,v 1.71 2008-09-30 23:50:02 lpoulson Exp $

######################################################################
# imports

import os
import datetime
import shutil
import tdl
import tarfile
if os.name == 'nt':
  import gzip
import zipfile
import sys
import re

from choices import ChoicesFile
from utils import TDLencode

######################################################################
# globals

ch = {}

hierarchies = {}

mylang = None
rules = None
irules = None
lrules = None
lexicon = None
roots = None

######################################################################
# Utility functions

# Given a choices variable identifying something that can have a
# name, return that name if it exists, otherwise return the variable.
# If label is None, then use the current iter_prefix with the trailing
# underscore shaved off.
def get_name(label=None):
  if not label:
    label = ch.iter_prefix()[:-1]
  name = ch.get_full(label + '_name')
  if not name:
    name = label
  return name


# ERB 2006-09-16 There are properties which are derived from the
# choices file as a whole which various modules will want to know about.
# The first example I have is the presence of auxiliaries.  Both the
# negation and yes-no questions modules have cases where they need to
# restrict lexical rules to applying to main verbs only, but only if
# there is in fact a distinction between main and auxiliary verbs (i.e.,
# they need to say [ AUX - ], but only if the feature AUX is defined).

# ERB 2006-10-15 I want this function to return true if an auxiliary is
# defined, even if it's not needed for negation or questions.

def has_auxiliaries_p():

  return ch.get_full('has-aux') == 'yes'

# Returns the verb type for lexical/main verbs.
def main_or_verb():
  if has_auxiliaries_p():
    return 'main-verb-lex'
  else:
    return 'verb-lex'


# ERB 2006-09-21 This function assembles an inflectional rule out
# of the appropriate information and adds it to irules.tdl.
# Assumes we consistently use either 'prefix' and 'suffix' or 'before'
# and 'after' as values in the html form.
# Should this actually be a method on TDLfile?

def add_irule(instance_name,type_name,affix_type,affix_form):

  rule = instance_name + ' :=\n'
  if affix_type == 'prefix' or affix_type == 'before':
    rule += '%prefix (* ' + affix_form + ')\n'
  elif affix_type == 'suffix' or affix_type == 'after':
    rule += '%suffix (* ' + affix_form + ')\n'

# TODO: generate error here.
#  else:
#    error 'probable script bug'

  rule += type_name + '.\n'

  irules.add_literal(rule)


######################################################################
# Hierarchy class

# Hierarchy:
# A class for storing, operating on, and saving to TDL a type
# hierarchy.  The hierarchy is stored as an array, each element of
# which is itself an array of three strings: a type, a supertype, and
# a comment.
class Hierarchy:
  # Initialize
  def __init__(self, name, type = ''):
    self.name = name
    self.type = type
    self.hierarchy = []

    self.supertypes = {}
    self.subtypes = {}
    self.leaves = set()
    self.coverage = {}


  def is_empty(self):
    return len(self.hierarchy) == 0


  # Add a type to the hierarchy
  def add(self, type, supertype, comment = ''):
    self.hierarchy += [ [ type, supertype, comment ] ]

  # Save the hierarchy to the passed TDLfile object.  The resulting
  # TDL will look like this:
  #
  # type1 := supertype1  ; comment1
  # type2 := supertype2  ; comment2
  # type3 := supertype3  ; comment3
  # ...
  def save(self, tdl_file, define = True):
    mylang.add_literal(';;; ' + self.name[0:1].upper() + self.name[1:])

    if define:
      tdl_file.add(self.name + ' := *top*.', '', True)

    for h in self.hierarchy:
      tdl_file.add(h[0] + ' := ' + h[1] + '.', h[2], True)

  # For each type in the hierarchy, calculate which types it is
  # the immediate supertype of, and save this information for later.
  def __calc_supertypes(self):
    self.supertypes = {}
    for h in self.hierarchy:
      if not h[0] in self.supertypes:
        self.supertypes[h[0]] = set()
      if not h[1] in self.supertypes:
        self.supertypes[h[1]] = set()

      self.supertypes[h[0]].add(h[1])


  # For each type in the hierarchy, calculate which types it is
  # the immediate subtype of, and save this information for later.
  def __calc_subtypes(self):
    self.subtypes = {}
    for h in self.hierarchy:
      if not h[0] in self.subtypes:
        self.subtypes[h[0]] = set()
      if not h[1] in self.subtypes:
        self.subtypes[h[1]] = set()

      self.subtypes[h[1]].add(h[0])


  # Calculate the leaf types (i.e. types with no subtypes) and save
  # this information for later.
  def __calc_leaves(self):
    self.__calc_subtypes()
    
    self.leaves = set()
    for st in self.subtypes:
      if len(self.subtypes[st]) == 0:
        self.leaves.add(st)


  # For each type in the hierarchy, calculate which leaf types it
  # covers, and save this information for later.
  def __calc_coverage(self):
    self.__calc_leaves()
    self.__calc_supertypes()
    
    self.coverage = {}
    for l in self.leaves:
      working = [ l ]
      while working:
        w = working[0]
        del working[0]
        if w != '*top*':
          if not w in self.coverage:
            self.coverage[w] = set()
          self.coverage[w].add(l)
          for st in self.supertypes[w]:
            working += [ st ]


  # Search the hierarchy for a type and return its comment, if any
  def get_comment(self, type):
    for h in self.hierarchy:
      if h[0] == type:
        return h[2]

    return ''


  # Search the hierarchy for a type covering all the types in type_set
  # and return it.  Type hierarchies as described in the questionnaire
  # may be insufficient for some purposes.  For example, implementing
  # the scale hierarchy of a direct-inverse language may require the
  # existence of a grouping of leaf types that requires that does not
  # exist.  This method will add such types to the hierarchy as
  # necessary.
  def get_type_covering(self, type_set):

    type_list = list(type_set)
    if len(type_list) == 1:
      return type_list[0]    

    if type(type_set) == 'list':
      type_set = set(type_set)

    self.__calc_coverage()
    cov = self.coverage

    # type_set may contain non-leaves, so construct a new all-leaf set
    new_set = set()
    for e in type_set:
      for l in cov[e]:
        new_set.add(l)

    # check for an existing type covering the right set of leaves
    for k in cov:
      if cov[k] == new_set:
        return k

    # Need to create a new type in the hierarchy:
    # If there are types in the hierarchy that have the same coverage,
    # then the approach where we distinguish nodes by their coverage
    # won't work.  In that case, simply create a new supertype under
    # the root.
    bad_hierarchy = False
    for k in cov:
      for l in cov:
        if k != l and cov[k] == cov[l]:
          bad_hierarchy = True
          break
        
    supers = []
    subs = []
    if bad_hierarchy:
      supers = [self.name]
      subs = type_set
    else:
      # Find types in the hierarchy that are supersets and subsets of
      for k in cov:
        if cov[k].issuperset(new_set):
          supers += [ k ]
        elif cov[k].issubset(new_set):
          subs += [ k ]

      # prune supers and subs
      toremove = set()
      for i in range(len(supers) - 1, -1, -1):
        for j in range(len(supers) -1, -1, -1):
          if i != j and cov[supers[i]].issuperset(cov[supers[j]]):
            toremove.add(i)
      remove_array = [e for e in toremove]
      remove_array.sort(reverse=True)
      for i in remove_array:
        del(supers[i])

      toremove = set()
      for i in range(len(subs) - 1, -1, -1):
        for j in range(len(subs) -1, -1, -1):
          if i != j and cov[subs[i]].issubset(cov[subs[j]]):
            toremove.add(i)
      remove_array = [e for e in toremove]
      remove_array.sort(reverse=True)
      for i in remove_array:
        del(subs[i])

    # figure out the name of the new type
    new_type = ''
    for h in self.hierarchy:
      covh = cov[h[0]]
      if len(covh.intersection(new_set)) == 0 and \
         len(covh.union(new_set)) == len(self.leaves):
        new_type = 'non-' + h[0]
        break
    if not new_type:
      new_type = '+'.join(subs)

    # now insert the new type between supers and subs, making sure to
    # remove any direct inheritance of the subs by the supers
    for i in range(len(self.hierarchy) - 1, -1, -1):
      if self.hierarchy[i][0] in subs and self.hierarchy[i][1] in supers:
        del(self.hierarchy[i])
    for s in supers:
      self.hierarchy += [ [new_type, s, ''] ]
    for s in subs:
      self.hierarchy += [ [s, new_type, ''] ]

    return new_type


######################################################################
# customize_feature_values(type_name, pos, features, cases)
#   In the current choices file context, go through the 'feat'
#   iterator and specify the feature/value pairs found to the
#   passed-in type.

def customize_feature_values(type_name, pos, features=None, cases=None, tdlfile=None):

  if not features:
    features = ch.features()
  if not cases:
    cases = ch.cases()
  if not tdlfile:
    tdlfile = mylang

  pos_geom_prefix = ''
  if pos == 'det':
    pos_geom_prefix = 'SYNSEM.LOCAL.CAT.VAL.SPEC.FIRST.'
  else:
    pos_geom_prefix = 'SYNSEM.'

  if pos == 'auxcomplement':
    iter_feat = 'compfeature'
  else:
    iter_feat = 'feat'

  ch.iter_begin(iter_feat)
  while ch.iter_valid():
    n = ch.get('name')
    v = ch.get('value').split(', ')

    if n == 'case':
      v = [canon_to_abbr(c, cases) for c in v]

    geom_prefix = pos_geom_prefix

    # The 'head' choice only appears on verb slots, and allows the user
    # to specify features on the subject and object as well
    h = ch.get('head')
#    geom_prefix = pos_geom_prefix
    if h == 'subj':
      geom_prefix += 'LOCAL.CAT.VAL.SUBJ.FIRST.'
    elif h == 'obj':
      geom_prefix += 'LOCAL.CAT.VAL.COMPS.FIRST.'
    elif h == 'higher':
      geom_prefix = 'SC-ARGS.FIRST.'
    elif h == 'lower':
      geom_prefix = 'SC-ARGS.REST.FIRST.'

    if pos == 'auxcomplement':
      geom_prefix += 'LOCAL.CAT.VAL.COMPS.FIRST.'

    geom = ''
    for f in features:
      if f[0] == n:
        geom = f[2]

    if geom:
      geom = geom_prefix + geom

    # If the feature has a geometry, just specify its value;
    # otherwise, handle it specially.
    if geom:
      if n in hierarchies:
        value = hierarchies[n].get_type_covering(v)
        tdlfile.add(type_name +
                    ' := [ ' + geom + ' ' + value + ' ].',
                    merge=True)
        if n == 'case' and ch.has_mixed_case():
          tdlfile.add(type_name +
                      ' := [ ' + geom + '-MARKED + ].',
                      merge=True)
      else:
        for value in v:
          tdlfile.add(type_name +
                      ' := [ ' + geom + ' ' + value + ' ].',
                      merge=True)
    elif n == 'argument structure':
      # constrain the ARG-ST to be passed up
      tdlfile.add(type_name + ' := [ ARG-ST #arg-st, DTR.ARG-ST #arg-st ].',
                  merge=True)

      # get the feature geometry of CASE
      for f in features:
        if f[0] == 'case':
          geom = f[2]

      for argst in v:
        # specify the subj/comps CASE values
        s_case = a_case = o_case = ''
        c = argst.split('-')
        if len(c) > 1:
          a_case = canon_to_abbr(c[0], cases)
          o_case = canon_to_abbr(c[1], cases)
          tdlfile.add(type_name + \
                      ' := [ ARG-ST < [ ' + \
                      geom + ' ' + a_case + ' ], [ ' +
                      geom + ' ' + o_case + ' ] > ].',
                      merge=True)
        else:
          s_case = canon_to_abbr(c[0], cases)
          tdlfile.add(type_name + \
                      ' := [ ARG-ST.FIRST. ' + \
                      geom + ' ' + s_case + ' ].',
                      merge=True)

    elif (n == 'negation' and v[0] == 'plus'):
      # ERB 2009-01-22 This is where we deal with the
      # negative affixes.  
      tdlfile.add(type_name + ':= \
                     [ C-CONT [ HOOK [ XARG #xarg,\
	                     LTOP #ltop,\
	                     INDEX #ind ],\
	              RELS <! event-relation &\
	                      [ PRED "_neg_r_rel",\
	                        LBL #ltop,\
	                        ARG1 #harg ] !>,\
	              HCONS <! qeq &\
	                       [ HARG #harg,\
	                         LARG #larg ] !> ],\
	              SYNSEM.LKEYS #lkeys,\
	            DTR [ SYNSEM [ LKEYS #lkeys,\
	                    LOCAL [ CONT.HOOK [ XARG #xarg,\
                                                INDEX #ind,\
	                                        LTOP #larg ],\
	                          CAT.HEAD verb]]]].',
                 'This lexical rule adds the neg_r_rel to the verb\'s\n\
	          RELS list.  It is instantiated by a spelling-changing\n\
	          rule as specified in irules.tdl.',
                  merge=True)
    elif(n=='OPT' and v[0] == 'plus'):
      # SS 2009-05-26 argument optionality is added to user defined types here
      if h == 'subj':
        tdlfile.add(type_name + ':= subj-drop-verb-lex.', merge = True)
      if h == 'obj':
        tdlfile.add(type_name + ':= obj-drop-verb-lex.', merge = True)

    elif(n=='OPT' and v[0] == 'minus'):
      if h == 'subj':
        tdlfile.add(type_name + ':= no-subj-drop-verb-lex.', merge = True)
      if h == 'obj':
        tdlfile.add(type_name + ':= no-obj-drop-verb-lex.', merge = True)
    
    elif (n=='overt-arg' and h == 'obj' and v[0] == 'not-permitted'):
      tdlfile.add(type_name + ' := [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT +].', merge = True)
    
    elif(n=='overt-arg' and h == 'subj') and v[0] == 'not-permitted':
      tdlfile.add( type_name + ' := [SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT +].', merge = True)

    elif (n=='dropped-arg' and h == 'obj' and v[0] == 'not-permitted'):
      tdlfile.add(type_name + ' := [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)
    
    #elif(n=='dropped-arg' and h == 'subj') and v[0] == 'not-permitted':
     # tdlfile.add( type_name + ' := [SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT -].', merge = True)

      
    ch.iter_next()
  ch.iter_end()


######################################################################
# customize_case()
#   Create the type definitions associated with the user's choices
#   about case.

def init_case_hierarchy():
  cm = ch.get('case-marking')
  cases = ch.cases()

  hier = Hierarchy('case')

  # For most case patterns, just make a flat hierarchy.  For fluid-s,
  # split-n and split-v, however, a more articulated hierarchy is required.
  if cm in ['nom-acc', 'erg-abs', 'tripartite', 'split-s', 'focus']:
    for c in cases:
      hier.add(c[2], 'case', c[1])
  elif cm in ['fluid-s']:
    abbr = canon_to_abbr('a+o', cases)
    for c in cases:
      if c[0] in ['a', 'o']:
        hier.add(c[2], abbr, c[1])
      else:
        hier.add(c[2], 'case', c[1])
  elif cm in ['split-n', 'split-v']:
    nom_a = canon_to_abbr('nom', cases)
    acc_a = canon_to_abbr('acc', cases)
    erg_a = canon_to_abbr('erg', cases)
    abs_a = canon_to_abbr('abs', cases)
    if cm == 'split-v':
      for c in cases:
        hier.add(c[2], 'case', c[1])
    else:  # 'split-n':
      hier.add('a', 'case', 'transitive agent')
      hier.add('s', 'case', 'intransitive subject')
      hier.add('o', 'case', 'transitive patient')
      for c in cases:
        if c[2] == erg_a:
          hier.add(c[2], 'a', c[1])
        elif c[2] == nom_a:
          hier.add(c[2], 'a', c[1])
          hier.add(c[2], 's', c[1])
        elif c[2] == abs_a:
          hier.add(c[2], 's', c[1])
          hier.add(c[2], 'o', c[1])
        elif c[2] == acc_a:
          hier.add(c[2], 'o', c[1])
        else:
          hier.add(c[2], 'case', c[1])

  if not hier.is_empty():
    hierarchies[hier.name] = hier


# customize_case_type()
#   Create a type for case

def customize_case_type():
  if 'case' in hierarchies:
    hierarchies['case'].save(mylang)


# customize_case_adpositions()
#   Create the appropriate types for case-marking adpositions

def customize_case_adpositions():
  cases = ch.cases()
  features = ch.features()

  if ch.has_adp_case():
    comment = \
      ';;; Case-marking adpositions\n' + \
      ';;; Case marking adpositions are constrained not to\n' + \
      ';;; be modifiers.'
    mylang.add_literal(comment)

    mylang.add('+np :+ [ CASE case ].')

    typedef = \
      'case-marking-adp-lex := basic-one-arg & raise-sem-lex-item & \
          [ SYNSEM.LOCAL.CAT [ HEAD adp & [ CASE #case, MOD < > ], \
                               VAL [ SPR < >, \
                                     SUBJ < >, \
                                     COMPS < #comps >, \
                                     SPEC < > ]], \
            ARG-ST < #comps & [ LOCAL.CAT [ HEAD noun & [ CASE #case ], \
                                            VAL.SPR < > ]] > ].'
    mylang.add(typedef)

    if ch.has_mixed_case():
      mylang.add('+np :+ [ CASE-MARKED bool ].')
      typedef = \
        'case-marking-adp-lex := [ ARG-ST < [ LOCAL.CAT.HEAD.CASE-MARKED - ] > ].'
      mylang.add(typedef)

    # Lexical entries
    lexicon.add_literal(';;; Case-marking adpositions')

    ch.iter_begin('adp')
    while ch.iter_valid():
      orth = ch.get('orth')

      # figure out the abbreviation for the case this adp marks
      cn = ''
      abbr = ''
      ch.iter_begin('feat')
      while ch.iter_valid():
        if ch.get('name') == 'case':
          cn = ch.get('value')
          break
        ch.iter_next()
      ch.iter_end()

      abbr = name_to_abbr(cn, cases)

      adp_type = TDLencode(abbr + '-marker')
      typedef = \
        adp_type + ' := case-marking-adp-lex & \
                        [ STEM < "' + orth + '" > ].'
      lexicon.add(typedef)

      customize_feature_values(adp_type, 'adp', tdlfile=lexicon)

      ch.iter_next()
    ch.iter_end()


def customize_case():
  customize_case_type()


def customize_direct_inverse():
  if not ch.get_full('scale1_feat1_name'):
    return

  mylang.add('verb :+ [ DIRECTION direction ].')
  hier = Hierarchy('direction')
  hier.add('dir', 'direction')
  hier.add('inv', 'direction')
  hier.save(mylang)

  if ch.has_SCARGS():
    mylang.add('word-or-lexrule :+ [ SC-ARGS list ].')
    mylang.add('lex-rule :+ [ SC-ARGS #1, DTR.SC-ARGS #1 ].')

  cases = ch.cases()
  features = ch.features()

  state = ch.iter_state()
  ch.iter_reset()

  # Figure out which features are involved in the hierarchy
  names = []  # feature names
  scale_max = 0
  ch.iter_begin('scale')
  while ch.iter_valid():
    scale_max += 1

    ch.iter_begin('feat')
    while ch.iter_valid():
      names.append(ch.get('name'))
      ch.iter_next()
    ch.iter_end()

    ch.iter_next()
  ch.iter_end()

  # Now pass through the scale, creating the direct-inverse hierarchy
  # pairwise
  supertype = 'dir-inv-scale'
  mylang.add_literal(';;; Scale for direct-inverse')
  mylang.add(supertype + ' := canonical-synsem.')
  for i in range(1, scale_max):
    values = {}  # for each feature, a set of values

    ch.iter_begin('scale' + str(i))

    # get the features on the first scale entry in this range
    ch.iter_begin('feat')
    while ch.iter_valid():
      name = ch.get('name')
      if name not in values:
        values[name] = set()
      values[name].add(ch.get('value'))

      ch.iter_next()
    ch.iter_end()

    # create the left type in the pair
    type = 'dir-inv-' + str(i)

    mylang.add(type + ' := ' + supertype + '.')

    for n in values:
      vset = values[n]

      if n == 'case':
        new_vset = set()
        for v in vset:
          new_vset.add(canon_to_abbr(v, cases))
        vset = new_vset

      geom = ''
      for f in features:
        if f[0] == n:
          geom = f[2]

      value = hierarchies[n].get_type_covering(vset)
      if value != n:  # don't bother if it doesn't constrain anything
        mylang.add(type + ' := [ ' + geom + ' ' + value + ' ].')

    # continuing 'scale'
    values = {}
    ch.iter_next()
    while ch.iter_valid():
      ch.iter_begin('feat')
      while ch.iter_valid():
        name = ch.get('name')
        if name not in values:
          values[name] = set()
        values[name].add(ch.get('value'))

        ch.iter_next()
      ch.iter_end()

      ch.iter_next()
    ch.iter_end()

    if i == scale_max:
      break

    # create the right type in the pair
    type = 'dir-inv-non-' + str(i)

    mylang.add(type + ' := ' + supertype + '.')

    for n in values:
      vset = values[n]

      if n == 'case':
        new_vset = set()
        for v in vset:
          new_vset.add(canon_to_abbr(v, cases))
        vset = new_vset

      geom = ''
      for f in features:
        if f[0] == n:
          geom = f[2]

      value = hierarchies[n].get_type_covering(vset)
      if value != n:  # don't bother if it doesn't constrain anything
        mylang.add(type + ' := [ ' + geom + ' ' + value + ' ].')

    supertype = type

  ch.iter_set_state(state)


# Return the number of items in the direct-inverse scale
def direct_inverse_scale_size():
  state = ch.iter_state()
  ch.iter_reset()

  scale_size = 0
  ch.iter_begin('scale')
  while ch.iter_valid():
    scale_size += 1
    ch.iter_next()
  ch.iter_end()

  ch.iter_set_state(state)

  return scale_size


######################################################################
# customize_person_and_number()
#   Create the type definitions associated with the user's choices
#   about person and number.

def init_person_hierarchy():
  hier = Hierarchy('person')

  for p in ch.persons():
    for st in p[1].split(';'):
      hier.add(p[0], st)

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def init_number_hierarchy():
  hier = Hierarchy('number')

  for n in ch.numbers():
    for st in n[1].split(';'):
      hier.add(n[0], st)

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def init_pernum_hierarchy():
  hier = Hierarchy('pernum')

  for pn in ch.pernums():
    for st in pn[1].split(';'):
      hier.add(pn[0], st)

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_person_and_number():
  if 'pernum' in hierarchies:
    mylang.add('png :+ [ PERNUM pernum ].')
    hierarchies['pernum'].save(mylang)
  else:
    if 'person' in hierarchies:
      mylang.add('png :+ [ PER person ].')
      hierarchies['person'].save(mylang)

    if 'number' in hierarchies:
      mylang.add('png :+ [ NUM number ].')
      hierarchies['number'].save(mylang)


######################################################################
# customize_gender()
#   Create the type definitions associated with the user's choices
#   about gender.

def init_gender_hierarchy():
  hier = Hierarchy('gender')

  for g in ch.genders():
    for st in g[1].split(';'):
      hier.add(g[0], st)

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_gender():
  if 'gender' in hierarchies:
    mylang.add('png :+ [ GEND gender ].')
    hierarchies['gender'].save(mylang)


######################################################################
# customize_other_features()
#   Create the type definitions associated with the user's choices
#   about other features.

def init_other_hierarchies():
  ch.iter_begin('feature')
  while ch.iter_valid():
    feat = ch.get('name')
    type = ch.get('type')

    hier = Hierarchy(feat, type)

    ch.iter_begin('value')
    while ch.iter_valid():
      val = ch.get('name')

      ch.iter_begin('supertype')
      while ch.iter_valid():
        stype = ch.get('name')

        hier.add(val, stype)

        ch.iter_next()
      ch.iter_end()

      ch.iter_next()
    ch.iter_end()

    if not hier.is_empty():
      hierarchies[hier.name] = hier

    ch.iter_next()
  ch.iter_end()


def customize_other_features():
  for name in hierarchies:
    h = hierarchies[name]
    feat = h.name
    type = h.type

    # if this hierarchy isn't handled elsewhere, handle it here
    if feat not in ['case', 'person', 'number', 'pernum', 'gender',
                    'form', 'tense', 'aspect', 'situation']:
      if type == 'head':
        mylang.add('head :+ [ ' + feat.upper() + ' ' + feat + ' ].')
      else:
        mylang.add('png :+ [ ' + feat.upper() + ' ' + feat + ' ].')

      # sfd: If it's an 'index' feature, we should make sure to strip it
      # out in the VPM

      h.save(mylang)


######################################################################
# customize_tense()
# Create tense feature value hierarchies per the user's choices 

def init_tense_hierarchy():
  hier = Hierarchy('tense')

  tdefn = ch.get('tense-definition')
  if tdefn:
    if tdefn == 'choose':
      ppflist = []
      for ten in ('nonfuture', 'nonpast', 'past', 'present', 'future' ):
        
        if ch.is_set(ten):
          if ten not in ppflist:
            hier.add(ten, 'tense')
          ch.iter_begin(ten + '-subtype')
          while ch.iter_valid():
            subtype = ch.get('name')
            hier.add(subtype, ten)
            
            ch.iter_next()
          ch.iter_end()
          
          if ten == 'nonfuture':
            for moreten in ('past', 'present'):
              if ch.is_set(moreten):
                hier.add(moreten, ten)
                ppflist.append(moreten)       

          if ten == 'nonpast':
            for moreten in ('present', 'future'):
              if ch.is_set(moreten):
                hier.add(moreten, ten)
                ppflist.append(moreten)

    elif tdefn == 'build':

      ch.iter_begin('tense')
      while ch.iter_valid():
        name = ch.get('name')

        ch.iter_begin('supertype')
        while ch.iter_valid():
          supername = ch.get('name')

          hier.add(name, supername)
          ch.iter_next()
        ch.iter_end()

        ch.iter_next()
      ch.iter_end()

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_tense():
  if 'tense' in hierarchies:
    hierarchies['tense'].save(mylang, False)


######################################################################
# customize_aspect()
# Create viewpoint aspect feature value definitions per the user's choices

def init_aspect_hierarchy():
  hier = Hierarchy('aspect')

  ch.iter_begin('aspect')
  while ch.iter_valid():
    name = ch.get('name')

    ch.iter_begin('supertype')
    while ch.iter_valid():
      supername = ch.get('name')
      
      hier.add(name, supername)
      ch.iter_next()
    ch.iter_end()
      
    ch.iter_next()
  ch.iter_end()

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_aspect():
  if 'aspect' in hierarchies:
    hierarchies['aspect'].save(mylang, False)

# customize_situation()
# Create situation aspect feature value definitions per the user's choices
 
def init_situation_hierarchy():
  hier = Hierarchy('situation')

  ch.iter_begin('situation')
  while ch.iter_valid():
    name = ch.get('name')

    ch.iter_begin('supertype')
    while ch.iter_valid():
      supername = ch.get('name')
      
      hier.add(name, supername)
      ch.iter_next()
    ch.iter_end()
      
    ch.iter_next()
  ch.iter_end()

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_situation():
  if 'situation' in hierarchies:
    mylang.add('situation := sort.')
    mylang.add('tam :+ [SITUATION situation].')
    hierarchies['situation'].save(mylang, False)

######################################################################
# customize_word_order()
#   Create the type definitions associated with the user's choices
#   about basic word order, including information about adpositions
#   and auxiliaries.

# ERB 2006-09-15 DOCUMENTATION

# 1. Statement of domain

# This module handles the basic word order facts for matrix declarative
# clauses, include permissible orders of major constituents (V, S, O),
# and (where applicable) determiner-noun order, adposition-NP order, and
# auxiliary-verb order.  Since the word order section and the basic vocabulary
# section are closely related, both are documented together here.

# 2. Seed strings/requirements of POS lexicon

# The phenomena covered by this module can be illustrated using the following
# lexical entries:

# det (determiner)
# s (subject)
# o (object)
# io (indirect object)
# tv (transitive verb)
# iv (intransitive verb)
# dtv (ditransitive verb)
# aux (auxiliary verb)
# p (adposition)

# In these seed strings, p and aux are assumed to be semantically
# empty.  Det does have semantic content which is distinct from the
# semantic relation introduced by the bare-np phrase.

# In the absence of a module for case (and in languages without case)
# both 's tv o' and 'o tv s' will parse in an ostensibly svo language.  We
# want to distinguish s and o anyway because we would expect those two strings to
# have different semantic representations in an svo language.  That is,
# you shouldn't be able to generate 'o tv s' from the semantics of 's tv o'
# in a strictly svo language.

# Seed strings, not all of which will have valid permutations in all languages.

# Note that his module does NOT handle argument optionality, so the seed
# strings given here don't illustrate it.

# These seed strings are written assuming sov order, prepositions, det-n,
# and auxiliaries which immediately follow the verbs they attach to.
# They allow for optional dets and optional adps.

# The module as written really only does anything interesting with io
# (indirect objects) in the case of free word order languages.  The lexicon
# does not currently elicit a ditransitive verb, however.

## Intransitive verb, transitive verb, det on s, o, both, neither
## p on s, o, both, neither, with and without det

# s iv
# det s iv
# s o tv
# det s det o tv
# det s o tv
# s det o tv
# p s iv
# p s o tv
# p s p o tv
# s p o tv
# p det s iv
# p det s o tv
# p det s p o tv
# det s p o tv
# p s det o tv
# p s p det o tv
# s p det o tv
# p det s det o tv
# p det s p det o tv
# det s p o det tv

## Semantically distinct seed strings from the above:

# s iv
# det s iv
# s o tv
# det s o tv
# det s det o tv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three.  All of these are semantically distinct
# ## from each other, and from the strings above.

# s io o dtv
# det s io o dtv
# s det io o dtv
# s io det o dtv
# det s det io o dtv
# det s io det o dtv
# s det io det o dtv
# det s det io det o dtv

# ## P is semantically empty, so the strings below all share semantics
# ## with something in the set above.

# ## Ditransitive verbs.  Det on no arguments, eachone separately
# ## each pair, all three. P on s argument only.

# p s io o dtv
# p det s io o dtv
# p s det io o dtv
# p s io det o dtv
# p det s det io o dtv
# p det s io det o dtv
# p s det io det o dtv
# p det s det io det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on io argument only.

# s p io o dtv
# det s p io o dtv
# s det p io o dtv
# s p io det o dtv
# det s p det io o dtv
# det s p io det o dtv
# s p det io det o dtv
# det s p det io det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on o argument only.

# s io p o dtv
# det s io p o dtv
# s det io p o dtv
# s io p det o dtv
# det s det io p o dtv
# det s io p det o dtv
# s det io p det o dtv
# det s det io p det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on s and io arguments only.

# p s p io o dtv
# p det s p io o dtv
# p s p det io o dtv
# p s p io det o dtv
# p det s p det io o dtv
# p det s p io det o dtv
# p s p det io det o dtv
# p det s p det io det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on s and o arguments only.

# p s io p o dtv
# p det s io p o dtv
# p s det io p o dtv
# p s io p det o dtv
# p det s det io p o dtv
# p det s io p det o dtv
# p s det io p det o dtv
# p det s det io p det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on io and o arguments only.

# s p io p o dtv
# det s p io p o dtv
# s p det io p o dtv
# s p io p det o dtv
# det s p det io p o dtv
# det s p io p det o dtv
# s p det io p det o dtv
# det s p det io p det o dtv

# ## Ditransitive verbs.  Det on no arguments, each one separately
# ## each pair, all three. P on all three arguments.

# p s p io p o dtv
# p det s p io p o dtv
# p s p det io p o dtv
# p s p io p det o dtv
# p det s p det io p o dtv
# p det s p io p det o dtv
# p s p det io p det o dtv
# p det s p det io p det o dtv

# ## All of the above, with aux added at the end.
# ## aux is semantically empty, so no new semantics here.

# s iv aux
# det s iv aux
# s o tv aux
# det s det o tv aux
# det s o tv aux
# s det o tv aux
# p s iv aux
# p s o tv aux
# p s p o tv aux
# s p o tv aux
# p det s iv aux
# p det s o tv aux
# p det s p o tv aux
# det s p o tv aux
# p s det o tv aux
# p s p det o tv aux
# s p det o tv aux
# p det s det o tv aux
# p det s p det o tv aux
# det s p o det tv aux
# s io o dtv aux
# det s io o dtv aux
# s det io o dtv aux
# s io det o dtv aux
# det s det io o dtv aux
# det s io det o dtv aux
# s det io det o dtv aux
# det s det io det o dtv aux
# p s io o dtv aux
# p det s io o dtv aux
# p s det io o dtv aux
# p s io det o dtv aux
# p det s det io o dtv aux
# p det s io det o dtv aux
# p s det io det o dtv aux
# p det s det io det o dtv aux
# s p io o dtv aux
# det s p io o dtv aux
# s det p io o dtv aux
# s p io det o dtv aux
# det s p det io o dtv aux
# det s p io det o dtv aux
# s p det io det o dtv aux
# det s p det io det o dtv aux
# s io p o dtv aux
# det s io p o dtv aux
# s det io p o dtv aux
# s io p det o dtv aux
# det s det io p o dtv aux
# det s io p det o dtv aux
# s det io p det o dtv aux
# det s det io p det o dtv aux
# p s p io o dtv aux
# p det s p io o dtv aux
# p s p det io o dtv aux
# p s p io det o dtv aux
# p det s p det io o dtv aux
# p det s p io det o dtv aux
# p s p det io det o dtv aux
# p det s p det io det o dtv aux
# p s io p o dtv aux
# p det s io p o dtv aux
# p s det io p o dtv aux
# p s io p det o dtv aux
# p det s det io p o dtv aux
# p det s io p det o dtv aux
# p s det io p det o dtv aux
# p det s det io p det o dtv aux
# s p io p o dtv aux
# det s p io p o dtv aux
# s p det io p o dtv aux
# s p io p det o dtv aux
# det s p det io p o dtv aux
# det s p io p det o dtv aux
# s p det io p det o dtv aux
# det s p det io p det o dtv aux
# p s p io p o dtv aux
# p det s p io p o dtv aux
# p s p det io p o dtv aux
# p s p io p det o dtv aux
# p det s p det io p o dtv aux
# p det s p io p det o dtv aux
# p s p det io p det o dtv aux
# p det s p det io p det o dtv aux

# 3. TDL Samples

# For a v-final language, with prepositions, auxiliaries which precede the verb,
# and det-n order, we should get the following in mylanguage.tdl.  (Actually, this
# is a more nicely formatted version of what we *do* get, I haven't tested it
# as tdl yet.)

# head :+ [ AUX bool ] .

# ; comp-head-phrase is restricted from taking prepositions as its head.
# ; comp-head-phrase is restricted from taking auxiliaries as its head. 

# comp-head-phrase := basic-head-1st-comp-phrase & head-final &
#    [ SYNSEM.LOCAL.CAT.HEAD +nvjrcdmo & [ AUX - ]].

# ; head-comp-phrase is only for prepositions and auxiliaries.

# head-comp-phrase := basic-head-1st-comp-phrase & head-initial &
#    [ SYNSEM.LOCAL.CAT.HEAD +vp [ AUX + ]].

# subj-head-phrase := basic-head-subj-phrase & head-final.

# ; Rules for building NPs.  Note that the Matrix uses SPR for
# ; the specifier of nouns and SUBJ for the subject (specifier) of verbs.

# head-spec-phrase := basic-head-spec-phrase & head-final.

# ; Bare NP phrase.  Consider modifying the PRED value of the quantifier relation
# ; introduced to match the semantic effect of bare NPs in your language.

# bare-np-phrase := basic-bare-np-phrase &
#    [ C-CONT.RELS <! [ PRED "exist_q_rel" ] !> ].

# And in rules.tdl, we get:

# comp-head := comp-head-phrase.
# head-comp := head-comp-phrase.
# subj-head := subj-head-phrase.
# head-spec := head-spec-phrase.
# bare-np := bare-np-phrase.

# The lexical types look like this:

# ;;; Lexical types

# ;;; Nouns

# noun-lex := basic-noun-lex &
#   basic-one-arg &
#   [ SYNSEM.LOCAL [ CAT.VAL [ SPR < #spr &
#                                    [ LOCAL.CAT.HEAD det ] >,
#                              COMPS < >,
#                              SUBJ < >,
#                              SPEC < > ] ],
#     ARG-ST < #spr > ] .

# obl-spr-noun-lex := noun-lex &
#   [ SYNSEM.LOCAL.CAT.VAL.SPR < [ OPT - ] > ] .

# ;;; Verbs

# verb-lex := basic-verb-lex &
#   [ SYNSEM.LOCAL [ CAT [ VAL [ SPR < >,
#                                SPEC < >,
#                                SUBJ < #subj > ] ],
#                    CONT.HOOK.XARG #xarg ],
#     ARG-ST < #subj &
#              [ LOCAL [ CAT.VAL [ SPR < >,
#                                  COMPS < > ],
#                        CONT.HOOK.INDEX #xarg ] ], ... > ] .

# intransitive-verb-lex := verb-lex &
#   intransitive-lex-item &
#   [ SYNSEM.LOCAL.CAT.VAL.COMPS < >,
#     ARG-ST < [ LOCAL.CAT.HEAD adp ] > ] .

# transitive-verb-lex := verb-lex &
#   transitive-lex-item &
#   [ SYNSEM.LOCAL.CAT.VAL.COMPS < #comps >,
#     ARG-ST < [ LOCAL.CAT.HEAD adp ], #comps &
#                                      [ LOCAL.CAT [ VAL [ SPR < >,
#                                                          COMPS < > ],
#                                                    HEAD adp ] ] > ] .

# ;;; Case-marking adpositions
# ;;; Case marking adpositions are constrained not to
# ;;; be modifiers.

# case-marking-adp-lex := basic-one-arg &
#   raise-sem-lex-item &
#   [ SYNSEM.LOCAL.CAT [ HEAD adp &
#                             [ MOD < > ],
#                        VAL [ SPR < >,
#                              SUBJ < >,
#                              COMPS < #comps >,
#                              SPEC < > ] ],
#     ARG-ST < #comps &
#              [ LOCAL.CAT [ HEAD noun,
#                            VAL.SPR < > ] ] > ] .


# ;;; Determiners
# ;;; SPEC is non-empty, and already specified by basic-determiner-lex.

# determiner-lex := basic-determiner-lex &
#   basic-zero-arg &
#   [ SYNSEM.LOCAL.CAT.VAL [ SPR < >,
#                            COMPS < >,
#                            SUBJ < > ] ] .



# 4. Description of cases handled

# For the major constituent orders, this module handles: all fixed
# orders of S,O, and V, V-final, V-initial and "free".  It allows for
# strict det-n and strict n-det, as well as strict P-NP and strict
# NP-P.  In addition, it allows auxiliaries to appear strictly left,
# strictly right or either to the left or to the right of the
# constituent they combine with.  The lexicon module allows for
# auxiliaries which combine with V (argument composition), VP
# (raising) or S (??), and contribute their own preds or not.
# The lexicon module also allows for each verb to select for NP or
# PP arguments in each position (subject/object), and for nouns
# to have obligatory, optional, or no determiners.

# It also creates a bare np phrase for every language, because
# a) all nouns need quantifiers and b) I suspect that all languages
# allow bare NPs in at least some cases.

# The free word order case does some interesting work with ditransitives
# in order to illustrate all 24 possible orders.  This involves allowing
# the second complement to be realized by the first.

# 5. Known unhandled cases

# The module currently does not support word order which varies
# according to clause type (e.g., matrix v. subordinate), V2 order,
# free order of determiners or adpositions with respect to nouns.  It
# also doesn't handle "splattered NP"-type free word order where the
# major constituents are not cohesive.

# There is no specialization of the bare-np phrase (to e.g., pronouns
# only, etc).

# The present lexicon module does not elicit any ditransitive verbs,
# and this word order module does not elicit any information about the
# relative ordering of complements when there is more than one, aside
# from allowing free order of direct and indirect objects in the free
# word order case.  The basic-head-1st-comp-phrase
# v. basic-head-2nd-comp-phrase distinction provided in matrix.tdl is
# a start in this direction, however (and indeed is used by the free
# word order module).

# In addition to adpositions and auxiliaries, there are other types of
# words which will eventually want to use the head-comp (and maybe
# head-subj or head-spec) phrases.  Doing so will undoubtedly require
# some additional modifications to the (already quite complex)
# functions determine_consistent_order() and specialize_word_order().
# These include complementizers, question particles, degree specifiers,
# and complement-taking substantives.

# 6. Description of tdl

# The general strategy is to take the basic head-complement,
# head-subject and head-specifier phrases provided by matrix.tdl, and
# cross-classify them with the types that determine linear precedence
# (head-initial and head-final).  In addition, to allow only the
# correct orders (in VSO, VOS, SOV, OSV) and to eliminate spurious
# ambiguity (in SVO and OVS), head-subject rules are constrained to be
# COMPS < > or head-complement rules are constrained to be SUBJ < >.

# Some trickiness comes in when the orders for adpositions and/or
# auxiliaries aren't consistent with the order of V and O, either
# because they are more constrained (e.g., free order of V,O,S, but
# prepositions only) or constrained to be opposite (an SOV language
# with prepositions).  In this case, we have both head-comp and
# comp-head rules, but one or both constrains its HEAD value (and
# therefore what type of head daughter it can have).  These
# constraints are either on the type of the HEAD value (making use of
# the disjunctive head types provided in head-types.tdl) or on the AUX
# value.  To simplify things, AUX is declared as a feature of head, so
# that a rule that says [AUX -] is e.g., compatible with [HEAD adp].

# The tdl for the lexical types is pretty straightforward, in the
# case of nouns and verbs.  They inherit from the relevant supertypes
# in matrix.tdl, link ARG-ST elements to VAL elements, and constrain
# other VAL lists to be empty.  They also give the HEAD value for
# each argument.  Nouns might further provide a value for OPT on the
# specifier.  Verbs identify the XARG with the first ARG-ST element's
# INDEX.  The determiners just inherit from basic-zero-arg and make
# empty VAL lists (maybe that should be on basic-zero-arg anyway?).
# The case-marking adpositions inherit from basic-one-arg and raise-sem-lex-item.
# They link their sole argument, an NP, to a COMPS list. Further, they
# are MOD < >.

# The trickiest lexical types are the auxiliaries.  They are cross-classified
# along three dimensions: V, VP or S complement, pred or no pred, and
# (for V or VP complement) NP v. PP subject.

# 7. Description of customization (python)

# I have attempted to keep each tdl statement (ascription of a particular
# constraint to a particular type) stated only once in this script,
# even if it gets used in multiple cases.  Those cases are handled with
# if statements which test either the input values directly (e.g.,
# the value chosen for word order) or derived properties of those input
# values (whether or not the order of adpositions and verbs with respect
# to their complements is 'consistent').

# customize_word_order() calls the following subroutines:

#  customize_major_constituent_order(), which emits types and
#  instances for head-subject and head-complement rules, without worrying
#  about adp or aux.  In order to make the tdl statements even more compact
#  while preserving a the head-comp v. comp-head naming convention,
#  this subroutine stores part of the appropriate type and rule names
#  in the variables hs (for head-subject) and hc (for head-complement).
#  Since this information is also useful for the other subroutines,
#  customize_major_constituent_order() returns it as a dictionary.

#  customize_np_order() emits the head-spec (or spec-head) rule
#  and a bare-np phrase.

#  determine_consistent_order() takes the word order (wo) and head-
#  complement order (hc) and determines whether the relative order
#  of aux and v and/or p and np requires special treatment given the
#  order of v and o.  It returns a dictionary storing the information
#  for aux and adp.

#  specialize_word_order() takes the head-complement order (hc) and
#  the dictionary returned by determine_consistent_order() and emits
#  additional tdl for types and instances as required.

# Further documentation is provided in comments within the subroutines.

# 8. Required changes to other modules

# None --- this module is likely to change as more get added though!

# ERB 2006-09-14
# First pass at translating from old perl script.

def customize_word_order():

  wo = ch.get('word-order')

# Add type definitions.

# Handle major constituent order first.  This function returns the hs and hc
# values that other parts of this code will want.

  linear_precedence = customize_major_constituent_order(wo)
  hs = linear_precedence['hs']
  hc = linear_precedence['hc']


# Head specifier rules

  customize_np_word_order()

# ERB 2006-09-14 Then add information as necessary to handle adpositions,
# free auxiliaries, etc.

#In general, we might also find word order sensitive to
#clause type (matrix v. subordinate) and dependent type.

  orders = determine_consistent_order(wo,hc)
  specialize_word_order(hc,orders)


def customize_major_constituent_order(wo):

# ERB 2006-09-14 The most elegant factoring of just the major
# constituent information uses the same type names for head-comp and
# comp-head phrases.  This doesn't scale when we have to worry about
# adpositions and auxiliaries (and other twists on word order) where
# we might want both comp-head and head-comp in a single language.
# To try to keep the elegant factoring, I'm going to store the
# type names in variables.

  hc = ''
  hs = ''

# This part of the code handles the following basic word orders:
# all six strict orders, V-final and V-initial.  These 8 possible
# orders can be grouped according to head-comp order, head-subj order,
# and whether or not complements must attach before subjects, or subjects before
# complements.  I'm treating SVO and OVS as having complements attaching
# lower.

# (Are there languages which allow all orders in which S attaches
# ouside O as basic word orders?  Likewise all cases where O attaches
# outside S?)

# ERB 2007-01-21 Moving to message-free universe, and now hypothesizing
# that all rules which attach subjects attend to clausal semantics.
# Thus, the head-subj rules that are defined here inherit from
# decl-head-subj-phrase (imp-head-subj-phrase is also available).

  comment = ';;; Phrasal types'
  mylang.add_literal(comment)

# ASF 2008-11-03 v2 analysis requires MC feature is not passed up to mother in
# head - comp and not from mod to mother, putting it back for other wo options

  if not wo == 'v2':
    mylang.add_literal(';Constraint on MC used to be part of matrix.tdl\n;' + 
               ';it applies to all wo implementations, except for v2')
    mylang.add('basic-head-comp-phrase :+\
                [ SYNSEM.LOCAL.CAT.MC #mc,\
                  HEAD-DTR.SYNSEM.LOCAL.CAT.MC #mc ].')
    mylang.add('basic-head-mod-phrase-simple :+\
                [ SYNSEM.LOCAL.CAT.MC #mc, \
                  NON-HEAD-DTR.SYNSEM.LOCAL.CAT.MC #mc ].')
  

# Head-comp order

  if wo == 'sov' or wo == 'osv' or wo == 'ovs' or wo == 'v-final':
    hc = 'comp-head'
    mylang.add(hc + '-phrase := basic-head-1st-comp-phrase & head-final.')

  if wo == 'svo' or wo == 'vos' or wo == 'vso' or wo == 'v-initial':
    hc = 'head-comp'
    mylang.add(hc + '-phrase := basic-head-1st-comp-phrase & head-initial.')

# Head-subj order

  if wo == 'osv' or wo == 'sov' or wo == 'svo' or wo == 'v-final':
    hs = 'subj-head'
    mylang.add(hs + '-phrase := decl-head-subj-phrase & head-final.')

  if wo == 'ovs' or wo == 'vos' or wo == 'vso' or wo == 'v-initial':
    hs = 'head-subj'
    mylang.add(hs + '-phrase := decl-head-subj-phrase & head-initial.')

# Complements attach before subjects

  if wo == 'ovs' or wo == 'vos' or wo == 'sov' or wo == 'svo':
    mylang.add(hs + '-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS < > ].')

# Subjects attach before complements
# ASF 2008-11-20 in order to allow for aux with vp-comp for VSO and OSV 
# languages, the standard analysis needs to be adapted to a LIGHT + 
# constraint on the hs-rule.

  auxcomp = ch.get('aux-comp')
  if wo == 'vso' or wo == 'osv':
    if has_auxiliaries_p() and auxcomp == 'vp':  
      mylang.add(hs + '-phrase := [ HEAD-DTR.SYNSEM.LIGHT + ].')
    else:
      mylang.add(hc + '-phrase := [ HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ < > ].')

# ERB 2006-09-14 Free word order is a big fat special case:

# Module for free word order, i.e., all possible orders of head, subj,
# comps (thinking initially about V, S, and O).  Use this with
# free-order-rules.tdl, which is partially redunant to
# V-initial-rules.tdl and V-final-rules.tdl.  The difference is that
# those currently don't have the head-2nd-comp rules.

# Just using the V-final and V-initial modules together is
# unsatisfactory, since that system gives multiple parses for V-medial
# sentences.  On the other hand, the SVO and OVS modules together will
# generate SOV and VOS words, but not VSO and OSV.  Any other
# combinations would (I believe) lead to respecifications of types
# (head-subj-phrase, etc) rather than multiple parallel types.

# The root of the problem seems to be that we need the subject to be
# able to attach inside the object(s) for VSO and OSV, but at the same
# time, we don't want complete flexibility on order of attachment when
# the verb is in the middle -- that would give spurious ambiguity.

# This solution adopts the xmod hierarchy to enforce right-first
# attachment.  That is, all arguments appears to the right of the verb
# must attach before all arguments appearing to the left.  The
# linguistic prediction of this analysis is that free word order
# languages do not have a consistent VP consituent, even when the verb
# and object are adjacent (OV order).

# Using a separate feature for tracking argument attachment (as
# opposed to modifier attachment).  We might be able to collapse these
# one day, but that's not obvious.

# ERB 2006-09-14 This looks like a case for :+, even in this code,
# since we're adding to something defined in matrix.tdl.


  if wo == 'free':
    mylang.add('synsem :+ [ ATTACH xmod ].',
               'We can\'t just use the V-final and V-initial word\n' +
               'order modules together to get a good free word order\n' +
               'module. The root of the problem seems to be that we\n' +
               'need the subject to be able to attach inside the\n' +
               'object(s) for VSO and OSV, but at the same time, we\n' +
               'don\'t want complete flexibility on order of attachment\n' +
               'when the verb is in the middle -- that would give\n' +
               'spurious ambiguity.  This solution adopts the xmod\n' +
               'hierarchy to enforce right-first attachment.  That is,\n' +
               'all arguments appears to the right of the verb must\n' +
               'attach before all arguments appearing to the left.  The\n' +
               'linguistic prediction of this analysis is that free\n' +
               'word order languages do not have a consistent VP\n' +
               'consituent, even when the verb and object are adjacent\n' +
               '(OV order).  Using a separate feature for tracking\n' +
               'argument attachment (as opposed to modifier\n' +
               'attachment).  We might be able to collapse these one\n' +
               'day, but that\'s not obvious.')
    
# ASF 2008-11-18, if free wo lgge has aux and aux precedes verb, 
# the enforced attachment must apply in the other direction.

    if has_auxiliaries_p() and  ch.get('aux-comp-order') == 'before':
      mylang.add('head-initial-head-nexus := head-initial & \
                [ SYNSEM.ATTACH rmod,\
                  HEAD-DTR.SYNSEM.ATTACH notmod-or-rmod ].')
      mylang.add('head-final-head-nexus := head-final &\
                [ SYNSEM.ATTACH lmod ].')
    else: 
      mylang.add('head-initial-head-nexus := head-initial & \
                [ SYNSEM.ATTACH lmod,\
                  HEAD-DTR.SYNSEM.ATTACH notmod-or-lmod ].')

      mylang.add('head-final-head-nexus := head-final &\
                [ SYNSEM.ATTACH rmod ].')

    mylang.add('head-mod-phrase :+\
                [ SYNSEM.ATTACH #attach,\
                  HEAD-DTR.SYNSEM.ATTACH #attach ].',
               'We\'ll need to add identification of ATTACH between\n\
mother and head-daughter for all other kinds of phrases\n\
if we do this.  Just for illustration, I\'m putting it\n\
in for head-adjunct phrases here:')


# ASF (2008-11-03) Another big special case: v2
#
# This implementation does Autronesian-type v2, but without discontinuous nps.
# The only word order constraint is that the (verbal) head of the phrase must
# be in second position.
# It can be preceded by a noun phrase, verb or verbal cluster.
# Interaction with auxiliaries is not implemented for now, because it is not
# clear what may occur (so auxiliaries can occur anywhere for now, as long as
# the v2 constraint is respected)
# Also note that the implementation may need to be revised when more complex
# phenomena (such as clause final verbal cluster and vp-fronting) are
# implemented
#
  
  if wo == 'v2':
    mylang.add('verbal-head-nexus := headed-phrase & \
                [ SYNSEM.LOCAL.CAT.HEAD verb ].')
    mylang.add('head-initial-head-nexus := head-initial & \
                [ SYNSEM.LOCAL.CAT.MC na & #mc, \
                  HEAD-DTR.SYNSEM.LOCAL.CAT.MC #mc ].') 
    mylang.add('head-final-head-nexus := head-final & \
                [ SYNSEM.LOCAL.CAT.MC bool, \
                  HEAD-DTR.SYNSEM.LOCAL.CAT.MC na ].')

#rules shared among free and v2

  if wo == 'free' or wo == 'v2':
    mylang.add('head-subj-phrase := decl-head-subj-phrase & head-initial-head-nexus.')
    mylang.add('subj-head-phrase := decl-head-subj-phrase & head-final-head-nexus.')
    mylang.add('head-comp-phrase := basic-head-1st-comp-phrase & head-initial-head-nexus.')
    mylang.add('comp-head-phrase := basic-head-1st-comp-phrase & head-final-head-nexus.')
    mylang.add('head-comp-phrase-2 := basic-head-2nd-comp-phrase & head-initial-head-nexus.')
    mylang.add('comp-head-phrase-2 := basic-head-2nd-comp-phrase & head-final-head-nexus.')


# Add rule definitions for major constituent order.

  if wo == 'free' or wo == 'v2':
    rules.add('head-comp := head-comp-phrase.')
    rules.add('head-subj := head-subj-phrase.')
    rules.add('comp-head := comp-head-phrase.')
    rules.add('subj-head := subj-head-phrase.')
    rules.add('head-comp-2 := head-comp-phrase-2.')
    rules.add('comp-head-2 := comp-head-phrase-2.')
  # Assume at this point that there's a good value of wo.
  # Rule names are stored in hs and hc, since they're the same as type names
  # without the -phrase suffix.
  else:
    rules.add(hc + ' :=  ' + hc + '-phrase.')
    rules.add(hs + ' :=  ' + hs + '-phrase.')

  return {'hs': hs, 'hc': hc}

# ERB 2006-09-15 Subroutine for handling NP rules.

def customize_np_word_order():

  if ch.get('has-dets') == 'yes':
    mylang.add(
      'head-spec-phrase := basic-head-spec-phrase.',
      'Rules for building NPs.  Note that the Matrix uses SPR for\n' +
      'the specifier of nouns and SUBJ for the subject (specifier) of verbs.')

    if ch.get('noun-det-order') == 'noun-det':
      mylang.add('head-spec-phrase := head-initial.')
    if ch.get('noun-det-order') == 'det-noun':
      mylang.add('head-spec-phrase := head-final.')

    rules.add('head-spec := head-spec-phrase.')


    # ERB 2006-09-14 I think that all languages have some form of
    # the Bare NP phrase.  Eventually there will be some choices about
    # this (given an appropriate module).  For now, use this stand in.

  mylang.add('bare-np-phrase := basic-bare-np-phrase &\
  [ C-CONT.RELS <! [ PRED \"exist_q_rel\" ] !> ].',
             'Bare NP phrase.  Consider modifying the PRED value of the quantifier relation\nintroduced to match the semantic effect of bare NPs in your language.')

  rules.add('bare-np := bare-np-phrase.')


# ERB 2006-09-14 Subroutine for figuring out the relationship of major
# constituent order to adpositions and auxiliaries.  Returns two values:
# for adp and aux.  It takes in the values of wo and hc determined in
# the course of creating the basic word order rules.


def determine_consistent_order(wo,hc):

  adp = 'easy'
  aux = 'easy'
  qpart_order = 'easy'

  # Is the ordering of adpositions consistent with the ordering of O and V?
  # Assuming that adpositions are consistent within a language (i.e., you won't
  # find subject postpositions and object prepositions).

  adporder = ''
  ch.iter_begin('adp')
  while ch.iter_valid():
    adporder = ch.get('order')
    ch.iter_next()
  ch.iter_end()

  # ERB 2006-10-05 Fixing bug in free word order case.

  if adporder:
    if wo == 'free':
      if adporder == 'before':
        adp = 'free-prep'
      elif adporder == 'after':
        adp = 'free-post'
    elif hc == 'comp-head' and adporder == 'before':
      adp = 'ov-prep'
    elif hc == 'head-comp' and adporder == 'after':
      adp = 'vo-post'
  
  # Now what about auxiliaries?
  # ASF 2008-12-07 for non-harmonic order and v (not vp) comps,
  # we need a different procedure (see if auxcomp...)
   
  if has_auxiliaries_p():
    auxcomp = ch.get('aux-comp')  
    if wo == 'free':
      if ch.get('aux-comp-order') == 'before':
        aux = 'free-auxv'
      elif ch.get('aux-comp-order') == 'after':
        aux = 'free-vaux'
    elif hc == 'comp-head' and ch.get('aux-comp-order') == 'before':
      if auxcomp == 'v':
        aux = 'auxv-rule'  
      else:
        aux = 'ov-auxv'
    elif hc == 'head-comp' and ch.get('aux-comp-order') == 'after':
      if auxcomp == 'v':
        aux = 'vaux-rule'
      else:
        aux = 'vo-vaux'
     
  # ERB 2006-10-05 And what about the order of question particles wrt
  # to other kinds of head-comp?  I'm assuming for now that question particles
  # and other complementizers will behave the same way.  Are there languages
  # in which that is not true?

  if ch.get('q-part-order'):
    if wo == 'free':
      if ch.get('q-part-order') == 'after':
        qpart_order = 'free-sq'
      elif ch.get('q-part-order') == 'before':
        qpart_order = 'free-qs'
    elif hc == 'comp-head' and ch.get('q-part-order') == 'before':
      qpart_order = 'ov-qs'
    elif hc == 'head-comp' and ch.get('q-part-order') == 'after':
      qpart_order = 'vo-sq'

   # return what we learned

  return {'adp': adp, 'aux': aux, 'qpart_order': qpart_order}


# find out whether verbal clusters

def determine_vcluster(auxcomp, auxorder, wo):

  vcluster = False

  if auxcomp == 'vp':    
    if (wo == 'v-initial' and auxorder == 'before') or (wo == 'v-final' and auxorder == 'after'):
      vcluster = True
  elif auxcomp == 'v':
    if ch.get('v-cluster') == 'yes' or wo == 'v-initial' or wo == 'v-final':
      vcluster = True
    if wo == 'sov' or wo == 'ovs' or wo == 'osv':
      if auxorder == 'before':        
        vcluster = True  
      elif wo == 'sov' or wo == 'ovs':
        vcluster = False 
    if wo == 'vos' or wo == 'svo' or wo == 'vso':
      if auxorder == 'after':
        vcluster = True
      elif wo == 'vos' or wo == 'svo':
        vcluster = False
  if not has_auxiliaries_p():
    vcluster = False
  return vcluster

# ERB 2006-09-15 Subroutine for emitting additional information about
# head-complement and head-subject rules as required for adpositions and
# auxiliaries.

# aux		 adp		head-comp	comp-head	#rules    add to rules.tdl
# ---		 ---		---------	---------	------    ----------------
# ov-auxv 	 ov-prep	v:AUX + | adp	~adp:AUX -	2         head-comp: both
# vo-vaux	 vo-post	~adp:AUX - 	v:AUX + | adp	2         comp-head: both
# free-auxv	 free-prep	unrestricted	~adp:AUX - 	2         --
# free-vaux      free-post	~adp:AUX -	unrestricted	2         --
# free-auxv	 free-post	~adp		AUX -		2         --
# free-vaux      free-prep	AUX -		~adp		2         --
# easy		 ov-prep	adp		~adp		2         head-comp: adp
# easy		 vo-post	~adp		adp		2         comp-head: adp
# easy		 free-prep	unrestricted	~adp		2         --
# easy		 free-post	~adp		unrestricted	2         --
# ov-auxv	 easy		v:AUX +		AUX -		2         head-comp: aux
# vo-vaux	 easy		AUX -		v:AUX +		2         comp-head: aux
#
# Not bothering with the case where adpositions aren't fixed in their order,
# since I don't believe it exists.

# ERB 2006-09-15 Trying to make each tdl snippet appear only once in this code.
# The individual constraints from the table above are:

# v:AUX + | adp    HEAD +vp & [ AUX + ]
# ~adp             HEAD +nvjrcdmo
# adp              HEAD adp
# AUX -            [ AUX - ]
# v:AUX +          HEAD verb & [ AUX + ]

# These can apply to either head-comp or comp-head, depending.

# ERB 2006-10-05 But: We need to worry about question particles now,
# too.  As I add to this and the space gets more complex, I wish that
# there was some what I could take advantage of the head-types hiearchy
# better.

# In particular, the ~adp constraint right now adds +nvjrcdmo.
# But, the same phrase type might need to be compatible with comp,
# so I have to weaken that do +nvjrdmo, and then further constrain it
# to +nvjrcdmo.  Likewise, ~comp boils down to +nvjrdmo, possibly
# further constrained to +nvjrpdmo.  But I can't just add both
# of those constraints, since the tdl won't compile (you can't add
# a type to a conjunction if its supertype or subtype is mentioned).

# My first pass at a solution is to first collect two kinds of information
# about each of head-comp and comp-head:

# head-comp-is is a list which stores positive statements about
# what can be the head of a head-comp phrase.  If the word order is
# free, we shouldn't see any statements here, because anything can be
# a head. (Similarly for comp-head-is.)

# head-comp-is-not is a list which stores negative statements about
# possible heads of head-comp phrase, i.e., what can't be the head.
# We will have interesting values here even in the free word order
# case unless all of the orders values are 'easy'.  (Similarly for
# comp-head-is-not)

# It's possible that I could do this all in one step, but somehow it's
# easier to keep my undestanding of it if I break it out like this.

def specialize_word_order(hc,orders):

  adp = orders['adp']
  aux = orders['aux']
  qpart_order = orders['qpart_order']
  auxcomp = ch.get('aux-comp')
  wo = ch.get('word-order')
  auxorder = ch.get('aux-comp-order')
  vcluster = determine_vcluster(auxcomp, auxorder, wo)
     
  # ASF 2008-12-07 If verbal cluster is present, introduce relevant feature
  # and pass-up in lex-rule.
  # Also add relevant constraint to basic-head-comp-phrase 

  if vcluster:
    mylang.add('lex-or-phrase-synsem :+ [ VERB-CL luk ].',
                'Introducing VERB-CL keeps track whether main-verb is present in cluster')
    mylang.add('lex-rule :+ [ SYNSEM.VERB-CL #vc, \
                              DTR.SYNSEM.VERB-CL #vc ].')
    mylang.add('basic-head-comp-phrase :+ [ SYNSEM.VERB-CL #vc, \
                       NON-HEAD-DTR.SYNSEM.VERB-CL #vc ].')
  # ERB 2006-09-15 First add head-comp or comp-head if they aren't
  # already there.  I don't think we have to worry about constraining
  # SUBJ or COMPS on these additional rules because they'll only be for
  # adp or auxv or qpart, so far

  if hc == 'comp-head' and (adp == 'ov-prep' or aux == 'ov-auxv' or qpart_order == 'ov-qs'):
    mylang.add('head-comp-phrase := basic-head-1st-comp-phrase & head-initial.')

  if hc == 'head-comp' and (adp == 'vo-post' or aux == 'vo-vaux' or qpart_order == 'vo-sq'):
    mylang.add('comp-head-phrase := basic-head-1st-comp-phrase & head-final.')

  # ASF 2008-11-18, special auxiliary rule that allows for auxiliaries 
  # to combine with v's when aux-comp order is not harmonic
  # the vcluster + constraint is added to head-comp-phrase, since this
  # aux-rule is always combined with the verbal cluster analysis.

  if aux == 'auxv-rule':
    mylang.add('''aux-comp-phrase := basic-marker-comp-phrase & marker-initial-phrase & 
                                   [ SYNSEM [ LOCAL.CAT.HEAD.FORM #vform,
                                              VERB-CL #vc ],
                                     MARKER-DTR.SYNSEM.LOCAL.CAT.HEAD verb & [ AUX +,
                                                                               FORM #vform ],
                                     NON-MARKER-DTR.SYNSEM [ LOCAL.CAT.HEAD verb,
                                                             VERB-CL #vc ] ].''')
    mylang.add('comp-head-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].')
  if aux == 'vaux-rule':
    mylang.add('''comp-aux-phrase := basic-marker-comp-phrase & marker-final-phrase &
                                   [ SYNSEM [ LOCAL.CAT.HEAD.FORM #vform,
                                              VERB-CL #vc ],
                                     MARKER-DTR.SYNSEM.LOCAL.CAT.HEAD verb & [ AUX +,
                                                                               FORM #vform ],
                                     NON-MARKER-DTR.SYNSEM [ LOCAL.CAT.HEAD verb,
                                                             VERB-CL #vc ] ].''')
    mylang.add('head-comp-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].')
   
  # add necessary restrictions to assure verb clusters
  # and special auxiliary rules for vso/osv and free word order.

  if vcluster:
    if wo == 'vso' or wo == 'free' or wo == 'v-initial':
      mylang.add('head-subj-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].') 
    if wo == 'osv' or wo == 'free' or wo == 'v-final':
      mylang.add('subj-head-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].')
    if (aux == 'vini-vc' and aux == 'vo-auxv' ) or wo == 'free': 
      mylang.add('head-comp-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].') 
    if (aux == 'vfin-vc' and aux == 'ov-vaux') or wo == 'free':
      mylang.add('comp-head-phrase := [ HEAD-DTR.SYNSEM.VERB-CL + ].')
    if wo == 'free' or wo == 'vso' or wo == 'osv':      
      if auxorder == 'before' and aux != 'ov-auxv':
        mylang.add('aux-comp-phrase := basic-head-1st-comp-phrase & head-initial & \
                    [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ], \
                      NON-HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD verb ].')
        aux = 'auxc'
      elif auxorder == 'after' and aux != 'vo-vaux':
        mylang.add('comp-aux-phrase := basic-head-1st-comp-phrase & head-final & \
                    [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ], \
                      NON-HEAD-DTR.SYNSEM.LOCAL.CAT.HEAD verb ].')
        aux = 'caux'  
      if wo == 'free':
        mylang.add('head-comp-phrase-2 := [ HEAD-DTR.SYNSEM.VERB-CL + ].')
        mylang.add('comp-head-phrase-2 := [ HEAD-DTR.SYNSEM.VERB-CL + ].') 
    
  # Add rules to rules.tdl when necessary

  if aux == 'ov-auxv' or adp == 'ov-prep' or qpart_order == 'ov-qs':
    rules.add('head-comp := head-comp-phrase.')

  if aux == 'vo-vaux' or adp == 'vo-post' or qpart_order == 'vo-sq':
    rules.add('comp-head := comp-head-phrase.')

  if aux == 'auxv-rule' or aux == 'auxc':
    rules.add('aux-comp := aux-comp-phrase.')

  if aux == 'vaux-rule' or aux == 'caux':
    rules.add('comp-aux := comp-aux-phrase.')

  # ERB 2006-09-15 AUX if we're going to mention it, so the tdl compiles.

  if aux != 'easy':
    mylang.add('head :+ [AUX bool].')

  # ERB 2006-10-05 Collect positive statements about head-comp/comp-head
  # We only need to do this is if the word order is not free, and we only
  # need to do it for one of head-comp or comp-head, depending on the order
  # of o and v.
  

  head_comp_is = []
  comp_head_is = []

  # VO order 
  if aux == 'vo-vaux':
     comp_head_is.append('aux')
  if adp == 'vo-post':
    comp_head_is.append('adp')
  if qpart_order == 'vo-sq':
    comp_head_is.append('comp')

  # OV order 

  if aux == 'ov-auxv':
    head_comp_is.append('aux')
  if adp == 'ov-prep':
    head_comp_is.append('adp')
  if qpart_order == 'ov-qs':
    head_comp_is.append('comp')

  # ERB 2006-10-05 Collect negative statements about head-comp/comp-head.
  # This needs to be done even if the word order is free.  It might need
  # to be done for both head-comp and comp-head in a free word order language
  # with inconsistent constraints on comp, adp, and aux.


  head_comp_is_not = []
  comp_head_is_not = []

  # when free word order has cluster, restriction on hc does not apply

  if vcluster and (aux == 'free-auxv' or aux == 'free-vaux'):
    aux = 'free-auxcl'

  if aux == 'free-auxv' or aux == 'ov-auxv' or aux == 'auxv-rule':
    comp_head_is_not.append('aux')
  if aux == 'free-vaux' or aux == 'vo-vaux' or aux == 'vaux-rule':
    head_comp_is_not.append('aux')
  if adp == 'free-prep' or adp == 'ov-prep':
    comp_head_is_not.append('adp')
  if adp == 'free-post' or adp == 'vo-post':
    head_comp_is_not.append('adp')
  if qpart_order == 'free-qs' or qpart_order == 'ov-qs':
    comp_head_is_not.append('comp')
  if qpart_order == 'free-sq'or qpart_order == 'vo-sq':
    head_comp_is_not.append('comp')


  # ERB 2006-10-05 Add constraints to head-comp/comp-head.

  # First the positive constraints.  We only have positive constraints if
  # the word order is not free. We should only have positive constraints for
  # one of head-comp and comp-head and negative constraints for the other.
  # In the free word order case, we might have negative constraints for each
  # one.

  # If only one part of speech type is allowed by the positive constraints,
  # we don't have a disjunctive type.

  # ASF for aux-comp and comp-aux, restriction should be AUX +
  # ASF for v-final and v-initial, added SUBJ < [] > constraint to form
  # a verbal cluster at the beginning or end of the sentence.
  # ASF 2009-04-21: should also be restricted to being a verb, if only one
  # non-standard order is present.


  if len(head_comp_is) == 1:
    head = head_comp_is[0]
    if head == 'aux':
      mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ] ].',
               'head-comp-phrase requires auxiliary heads.')
      if wo == 'v-final' and auxcomp == 'vp': 
        mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.VAL.SUBJ < [ ] > ].')
    else:
      mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'head-comp-phrase requires things that are [ HEAD ' + head + ' ].') 

  if len(comp_head_is) == 1:
    head = comp_head_is[0]
    if head == 'aux':
      mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ] ].',
               'comp-head-phrase requires auxiliary heads.')      
      if wo == 'v-initial' and auxcomp == 'vp':
        mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.VAL.SUBJ < [ ] > ].')
    else:
      mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'comp-head-phrase requires things that are [ HEAD ' + head + ' ].')

  # Now the case where we do have disjunctive constraints.   NB: The order
  # here is important, since we're constructing the string which has to
  # correspond to the disjunctive head type.  While those are logically just
  # disjunctions, as far as the LKB is concerned, they're type names, so
  # we need an exact string match.

  # +nvjrcdmo.
  # +nvjrpdmo.

  
  if len(head_comp_is) > 1:
    head = '+'
    auxresthc = False
    if head_comp_is.count('aux'):
      head += 'v'
      auxresthc = True 
    if head_comp_is.count('adp'):
      head += 'p'
    if head_comp_is.count('comp'):
      head += 'c'

    mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'head-comp-phrase requires things that are one of: ' + str(head_comp_is))
    if auxresthc:
      mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX + ].')

  if len(comp_head_is) > 1:
    head = '+'
    auxrestch = False
    if comp_head_is.count('aux'):
      head += 'v'
      auxrestch = True
    if comp_head_is.count('adp'):
      head += 'p'
    if comp_head_is.count('comp'):
      head += 'c'

    mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'comp-head-phrase requires things that are one of: ' + str(head_comp_is))
    if auxrestch:
      mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX + ].')

  # Now the negative constraints.  This is where we extracted the
  # information that head-comp or comp-head can't be certain things.
  # Of course, in tdl we only have positive constraints.  So, we have
  # to translate the information to positive constraints.  Currently,
  # these will always involve disjunctive types, since we have more
  # pos types than things we're collecting negative info about.  The
  # other case is that we have no negative constraints, in which case
  # there's nothing to do.  We can just leave the HEAD value
  # completely underspecified.

  if head_comp_is_not.count('aux'):
    mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX - ].')
    head_comp_is_not.remove('aux')

  if len(head_comp_is_not) > 0:
    head = '+n'
    if head_comp_is_not.count('verb') == 0:
      head += 'v'
    head += 'jr'
    if head_comp_is_not.count('adp') == 0:
      head += 'p'
    if head_comp_is_not.count('comp') == 0:
      head += 'c'
    head += 'dmo'

    mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'The head of head-comp-phrase can\'t be: ' + str(head_comp_is_not))

  if comp_head_is_not.count('aux'):
    mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX - ].')
    comp_head_is_not.remove('aux')

  if len(comp_head_is_not) > 0:
    head = '+n'
    if comp_head_is_not.count('verb') == 0:
      head += 'v'
    head += 'jr'
    if comp_head_is_not.count('adp') == 0:
      head += 'p'
    if comp_head_is_not.count('comp') == 0:
      head += 'c'
    head += 'dmo'

    mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD ' + head + ' ].',
               'The head of comp-head-phrase can\'t be: ' + str(comp_head_is_not))


# ERB 2006-10-05 Below is what I had before I had to generalize because
# of addition of qpart_order.

# # The ~adp constraint and the ~comp constraint

#   if adp == 'ov-prep' or adp == 'free-prep':
#     mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD +nvjrcdmo ].',
#                'comp-head-phrase is restricted from taking prepositions as its head.')

#   if adp == 'vo-post' or adp == 'free-post':
#     mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD +nvjrcdmo ].',
#                'head-comp-phrase is restricted from taking adpositions as its head.')


# # And the opposite cases (adp, V:AUX + | adp)

#   if adp == 'ov-prep' and aux == 'easy':
#     mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD adp ].',
#                'head-comp-phrase is only for prepositions.')

#   if adp == 'ov-prep' and aux == 'ov-auxv':
#     mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD +vp & [ AUX + ] ].',
#                'head-comp-phrase is only for prepositions and auxiliaries.')

#   if adp == 'vo-post' and aux == 'easy':
#     mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD adp ].',
#                'comp-head-phrase is only for postpositions.')

#   if adp == 'vo-post' and aux == 'vo-vaux':
#     mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD +vp & [ AUX + ] ].',
#                'comp-head-phrase is only for postpositions and auxiliaries.')

# # The [AUX -] constraint

#   if aux == 'vo-vaux' or aux == 'free-vaux':
#     mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX - ].',
#                'head-comp-phrase is restricted from taking auxiliaries as its head.')

#   if aux == 'ov-auxv' or aux == 'free-auxv':
#     mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD.AUX - ].',
#                'comp-head-phrase is restricted from taking auxiliaries as its head.')

# # The v:AUX + constraint

#   if aux == 'ov-auxv' and adp == 'easy':
#     mylang.add('head-comp-phrase := [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ]].',
#                'head-comp-phrase is only for auxiliaries.')

#   if aux == 'vo-vaux' and adp == 'easy':
#     mylang.add('comp-head-phrase := [ SYNSEM.LOCAL.CAT.HEAD verb & [ AUX + ]].',
#                'comp-head-phrase is only for auxiliaries.')


######################################################################
# customize_sentential_negation()
#   Create the type definitions associated with the user's choices
#   about sentential negation.

# ERB 2006-10-05 DOCUMENTATION

# 1. Statement of domain

# This module handles the expression of sentential negation.  It
# provides two general strategy types (inflection v. adverb), several
# variations on each type, and what I believe to be an exhaustive listing
# of the possible ways of combining the two strategies.

# 2. Seed strings/requirements of POS lexicon

# In addition to the lexical entries given in the word order module,
# this module requires:

# neg (negative adverb)
# -neg (negative suffix)
# neg- (negative prefix)

# Note: at some point, the permutation machinery will need to do
# interesting things with affix order.  For now, there's not really
# enough affixes to worry about it.

# These seed strings are designed to work with languages that require
# dets and Ps as well as those that do not.  They are written assuming
# sov order, and use a transitive frame as the base to make the testing
# a little more interesting (e.g., when you have aux involved).  For
# the aux case, I'm assuming an auxiliary that follows the verb, and takes
# a VP complement (subject raising).

## These seed strings should each have one of two semantic representations,
## the only difference being the presence v. absence of det.  So,
## these two seed strings, parsed using a grammar that has negative
## adverbs as independent modifiers to the left o V, should give the
## two MRSs that we need:  (Once again, I'm assuming semantically empty aux.)

# s o neg tv
# det s det o neg tv

## Negative adverb --- the module allows for attachment at V, VP, and S,
## and to the left, right, or either.  Since we'll get all of these
## positions (and more!) by doing the permutation then, I'm just doing
## one set with a negative adverb, using the left of V placement:

# s o neg tv
# det s det o neg tv
# p s p o neg tv
# p det s p det o neg tv
# det s det o neg tv aux
# p det s p det o tv neg aux
# s o tv neg aux
# p s p o tv neg aux

# ## Prefix, on main verbs and aux:

# s o neg-tv
# det s det o neg-tv
# p s p o neg-tv
# p det s p det o neg-tv
# s o tv neg-aux
# det s det o tv neg-aux
# p s p o tv neg-aux
# p det s p det o tv neg-aux

# ## Suffix, on main verbs and aux:

# s o tv-neg
# det s det o tv-neg
# p s p o tv-neg
# p det s p det o tv-neg
# s o tv aux-neg
# det s det o tv aux-neg
# p s p o tv aux-neg
# p det s p det o tv aux-neg

# ## Adverb plus prefix, on main verbs and aux:

# s o neg neg-tv
# det s det o neg neg-tv
# p s p o neg neg-tv
# p det s p det o neg neg-tv
# s o tv neg neg-aux
# det s det o tv neg neg-aux
# p s p o tv neg neg-aux
# p det s p det o tv neg neg-aux

# ## Adverb plus suffix, on main verbs and aux:

# s o neg tv-neg
# det s det o neg tv-neg
# p s p o neg tv-neg
# p det s p det o neg tv-neg
# s o tv neg aux-neg
# det s det o tv neg aux-neg
# p s p o tv neg aux-neg
# p det s p det o tv neg aux-neg



# Unhandled case:  Main verbs take inflection + adverb, auxiliaries only
# inflection (or vice versa).  Negation involves two markers, one on
# either side of the constituent.  Negation involves two markers, one
# on either side of the constituent.

# ERB 2006-09-16 First pass at replicating functionality from
# perl script.

def customize_sentential_negation():

  # ERB 2006-09-16 Calculate a bunch of derived properties based on the
  # inputs they gave for negation.  The same thing (e.g., negation via
  # inflection on the main verb) gives a very different output depending
  # on whether there are other options (negation via selected adverb)
  # and how they combine.

  # ERB 2009-01-23 This is all moot right now since the interim system
  # doesn't do the interaction between the two, but it probably won't 
  # break anything to leave it in.

  advAlone = ''
  multineg = ch.get('multi-neg')
  if ch.get('adv-neg') == 'on' or multineg == 'comp':
    advAlone = 'always'
  if multineg == 'both-opt' or multineg == 'adv-obl':
    advAlone = 'sometimes'
  if multineg == 'both-obl' or multineg == 'infl-obl':
    advAlone = 'never'

  # ERB 2006-09-16 TODO: The perl script had an else on the above if
  # statment which generated a "probable script error" if we fell into
  # it.  It's probably good idea to put that in here, too.

  if ch.get('adv-neg') == 'on' and ch.get('neg-adv') == 'sel-adv':
    create_neg_add_lex_rule(advAlone)
    create_neg_adv_lex_item(advAlone)

  if ch.get('infl-neg') == 'on' and multineg != 'both-obl' and multineg != 'adv-obl':
    create_neg_infl_lex_rule()

  # ERB 2009-01-23 Migrating negation to modern customization system.
  # This intermediate version only does independent adverbs, and so
  # I'm removing ch.get('neg-adv') == 'ind-adv' as a second part of
  # the test below.

  if ch.get('adv-neg') == 'on': # and ch.get('neg-adv') == 'ind-adv':
    if advAlone == 'never':
      # Override user input: multi-neg as bothobl or inflobl means
      # we go with the selected adverb analysis.
      create_neg_add_lex_rule(advAlone)

    create_neg_adv_lex_item(advAlone)

# ERB 2006-09-21 neg-add-lex rule, for negation strategies that involve
# selected adverbs.

def create_neg_add_lex_rule(advAlone):

  # ERB 2006-09-17 The lexical rule conditions both need these
  # variables, so declare them here.

  pre = ''
  suf = ''
  orth = ''
  rule = ''

  # This first bit is shared by all the grammar types where we want
  # the neg-add-lex-rule.

  # ERB 2006-09-21 The value of COMPS on the mother is prettier
  # with the . notation rather than FIRST/REST, but for now tdl.py
  # isn't handling that case.
  #                                 COMPS < [ LOCAL [ CONT [ HOOK [ INDEX #negind,\
  #                                                                  LTOP #negltop ],\
  #                                                          HCONS <! [ LARG #larg ] !> #]],\
  #                                                   LKEYS.KEYREL.PRED \"_neg_r_rel\" ] . #comps > ],\

  mylang.add('''neg-add-lex-rule := local-change-only-lex-rule &
                       same-ctxt-lex-rule &
                       same-agr-lex-rule &
                       same-head-lex-rule &
                       same-hc-light-lex-rule &
                       same-posthead-lex-rule &
     [ SYNSEM.LOCAL [ CAT.VAL [ SUBJ #subj,
                                  SPR #spr,
                                  SPEC #spec ,
                                  COMPS [ FIRST [ LOCAL.CONT [ HOOK [ INDEX #negind,
                                                                      LTOP #negltop ],
                                                               HCONS <! [ LARG #larg ] !> ],
                                                  LKEYS.KEYREL.PRED "_neg_r_rel" ],
                                          REST #comps ]],
                        CONT.HOOK [ INDEX #negind,
                                      LTOP #negltop,
                                      XARG #xarg ]],
        DTR lex-item &  [ SYNSEM.LOCAL [ CAT [ VAL [ SUBJ #subj,
                                                     SPR #spr,
                                                     SPEC #spec,
                                                     COMPS #comps ],
                                               HEAD verb ],
                                         CONT.HOOK [ LTOP #larg,
                                                     XARG #xarg ]]]].''',
                                               '''This lexical rule adds a selected negative\n
                                               adverb to the beginning of the COMPS list''')

  #Decide what to do with AUX value.

  if ch.get('neg-sel-adv') == 'aux':
    mylang.add('neg-add-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX + ].'
               'This rule applies only to auxiliaries.')

  if ch.get('neg-sel-adv') == 'main' and has_auxiliaries_p():
    mylang.add('neg-add-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX - ].'
               'This rule applies only to main verbs.')

    #Make subtypes and instances as appropriate, depending on advAlone condition.

  if advAlone == 'always':
    mylang.add('neg-add-lex-rule := constant-lex-rule.'
               'Thie type is instantiated in lrules.tdl.')

    lrules.add('neg-add-lr := neg-add-lex-rule.')


    # TODO: I really just want to add a comment to this type in this case.  Will
    # this syntax do it?  If not, is there some other syntax in tdl.py that will?

  if advAlone == 'sometimes':
    mylang.comment('neg-add-lex-rule',
               'This type has subtypes instantiated by instances in both\n\
               irules.tdl and lrules.tdl.')
    mylang.add('infl-neg-add-lex-rule := neg-add-lex-rule & inflecting-lex-rule.')
    mylang.add('const-neg-add-lex-rule := neg-add-lex-rule & constant-lex-rule.')

    lrules.add('neg-add-lr := const-neg-add-lex-rule.')

    add_irule('neg-add-ir','infl-neg-add-lex-rule',ch.get('neg-aff'),ch.get('neg-aff-orth'))

  if advAlone == 'never':
    mylang.add('neg-add-lex-rule := inflecting-lex-rule.'
               'This type is instantiated in irules.tdl.')

    add_irule('neg-add-ir','neg-add-lex-rule',ch.get('neg-aff'),ch.get('neg-aff-orth'))

# ERB 2006-09-21 Create negative inflection lexical rule
#Inflection without selected adverb
#This one adds the '_neg_r_rel, and as such is only used
#when inflection appears alone (infl strategy only, both
#strategies with multi-neg = comp, bothopt, inflobl).

#Spell _neg_r_rel with leading _ even though it is introduced
#by the lexical rule so that "the cat didn't sleep" and "the
#cat did not sleep" have the same representation.

#Copying up LKEYS here because I use the KEYREL.PRED to select
#the neg adv in the neg-add-lex-rule.  We don't want the output
#of this rule to be a possible first complement to a neg-add aux.
#If we find another way to select the neg adv, something will
#probably need to be changed here.

#ERB 2007-02-26 Fixing a bug here: The rule's C-CONT.HOOK.INDEX
#should be identified with the DTR's INDEX, not with the ARG0
#of the _neg_r_rel.

def create_neg_infl_lex_rule():

  mylang.add('neg-infl-lex-rule := cont-change-only-lex-rule &\
	                     inflecting-lex-rule &\
	   [ C-CONT [ HOOK [ XARG #xarg,\
	                     LTOP #ltop,\
	                     INDEX #ind ],\
	              RELS <! event-relation &\
	                      [ PRED "_neg_r_rel",\
	                        LBL #ltop,\
	                        ARG1 #harg ] !>,\
	              HCONS <! qeq &\
	                       [ HARG #harg,\
	                         LARG #larg ] !> ],\
	     SYNSEM.LKEYS #lkeys,\
	     DTR lex-item & \
	         [ SYNSEM [ LKEYS #lkeys,\
	                    LOCAL [ CONT.HOOK [ XARG #xarg,\
                                                INDEX #ind,\
	                                        LTOP #larg ],\
	                          CAT.HEAD verb]]]].',
             'This lexical rule adds the neg_r_rel to the verb\'s\n\
	RELS list.  It is instantiated by a spelling-changing\n\
	rule as specified in irules.tdl.')

  if ch.get('neg-infl-type') == 'aux':
    mylang.add('neg-infl-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX + ].',
               'This rule applies only to auxiliaries.')

  if ch.get('neg-infl-type') == 'main' and has_auxiliaries_p():
    mylang.add('neg-infl-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX - ].',
               'This rule applies only to main verbs.')

  add_irule('neg-infl-lr','neg-infl-lex-rule',ch.get('neg-aff'),ch.get('neg-aff-orth'))

# ERB 2006-09-22 Create lexical types and lexical entries for

def create_neg_adv_lex_item(advAlone):

  mylang.add('''neg-adv-lex := basic-scopal-adverb-lex &
                 [ SYNSEM.LOCAL.CAT [ VAL [ SPR < >,
                                            COMPS < >,
                                            SUBJ < > ],
                                      HEAD.MOD < [ LOCAL.CAT.HEAD verb ] > ]].''',
             'Type for negative adverbs.')

  # ERB 2006-10-06 Below was advAlone == 'always', but that seems wrong.
  # changing it to advAlone == 'never' being the case where we don't want
  # the adverb to be a modifier.

  if advAlone == 'never':
    mylang.comment('neg-adv-lex','''Constrain the MOD value of this adverb to keep\n
    it from modifying the kind of verbs which can select it,\n
    To keep spurious parses down, as a starting point, we have\n
    assumed that it only modifies verbs (e.g., non-finite verbs).''')

  if ch.get('neg-order') == 'before':
    mylang.add('neg-adv-lex := [ SYNSEM.LOCAL.CAT.POSTHEAD - ].')
  elif ch.get('neg-order') == 'after':
    mylang.add('neg-adv-lex := [ SYNSEM.LOCAL.CAT.POSTHEAD + ].')

  if ch.get('neg-mod') == 's':
    mylang.add('''neg-adv-lex := [ SYNSEM.LOCAL.CAT.HEAD.MOD.FIRST.LOCAL.CAT.VAL [ SUBJ null,
                                                                                   COMPS null ]].''')
  elif ch.get('neg-mod') == 'vp':
    mylang.add('''neg-adv-lex := [ SYNSEM.LOCAL.CAT.HEAD.MOD.FIRST.LOCAL.CAT.VAL [ SUBJ cons,
                                                                                   COMPS null ]].''')
  elif ch.get('neg-mod') == 'v':
    mylang.add('''neg-adv-lex := [ SYNSEM.LOCAL.CAT.HEAD.MOD.FIRST.LIGHT + ].''')
    mylang.add('verb-lex := [ SYNSEM.LOCAL.CAT.HC-LIGHT - ].','''verb-lex is HC-LIGHT - to allow us to pick out\n
    lexical Vs for V-level attachment of negative adverbs.''')

  # ERB 2006-09-22 Validation should really make sure we have a value of
  # neg-adv-orth before we get here, but just in case, checking first, since
  # the script gets really unhappy if I try to write to an empty type.

  if(ch.get('neg-adv-orth')):
    orth = ch.get('neg-adv-orth')
    lexicon.add(TDLencode(orth) + ' := neg-adv-lex &\
                [ STEM < \"'+ orth +'\" >,\
                  SYNSEM.LKEYS.KEYREL.PRED \"_neg_r_rel\" ].')


  # ERB 2006-10-06 And of course we need the head-modifier rules, if we're
  # going to have an independent modifier.  While we're at it, we need to
  # contrain the MOD value on the rest of the head types to keep them
  # from going nuts.

  if advAlone != 'never':
    rules.add('head-adj-int := head-adj-int-phrase.',
              'Rule instances for head-modifier structures. Corresponding types\n' +
              'are defined in matrix.tdl.  The matrix customization script did\n' +
              'not need to add any further constraints, so no corresponding tyes\n' +
              'appear in ' + ch.get('language').lower() + '.tdl')
    rules.add('adj-head-int := adj-head-int-phrase.')
    rules.add('head-adj-scop := head-adj-scop-phrase.')
    rules.add('adj-head-scop := adj-head-scop-phrase.')

    mylang.add('+nvcdmo :+ [ MOD < > ].',
               'This grammar includes head-modifier rules.  To keep\n' +
               'out extraneous parses, constrain the value of MOD on\n' +
               'various subtypes of head.  This may need to be loosened later.\n' +
               'This constraint says that only adverbs, adjectives,\n' +
               'and adpositions can be modifiers.')

######################################################################
# Coordination
#   Create the type definitions associated with the user's choices
#   about coordination.

# sfd 2006-09-24 DOCUMENTATION
#
# 1. Statement of domain
#
# This module handles coordination of various phrase types (currently
# N, NP, VP, and S).  It relies on choices in the Coordination section
# of the questionnaire.
#
# 2. Seed strings/requirements of POS lexicon
#
# The phenomena covered by this module can be illustrated using the following
# lexical entries:
#
# det (determiner)
# s1 (subject noun)
# s2 (subject noun)
# s3 (subject noun)
# iv1 (intransitive verb)
# iv2 (intransitive verb)
# iv3 (intransitive verb)
# co (conjunction)
# -co or co- (affix versions of the conjunction)
#
# Seed strings, not all of which will have valid permutations in all languages.
#
# These seed strings are written assuming sov order, det-n order, and
# mandatory determiners.  Each section below will show the coordination
# of one phrase type in with several different coordination strategies,
# namely:
#   monosyndeton word before
#   monosyndeton word after
#   monosyndeton affix before (for N only)
#   monosyndeton affix after  (for N only)
#   polysyndeton word before
#   polysyndeton word after
#   polysyndeton affix before (for N only)
#   polysyndeton affix after  (for N only)
#   omnisyndeton word before
#   omnisyndeton word after
#   omnisyndeton affix before (for N only)
#   omnisyndeton affix after  (for N only)
#   asyndeton
#
## Coordination of nouns (each group of sentences should have the
## same semantic representation, though with different grammars)
#
# det s1 s2 co s3 iv1
# det s1 s2 s3 co iv1
# det s1 s2 co-s3 iv1
# det s1 s2 s3-co iv1
#
# det s1 co s2 co s3 iv1
# det s1 s2 co s3 co iv1
# det s1 co-s2 co-s3 iv1
# det s1 s2-co s3-co iv1
#
# det co s1 co s2 co s3 iv1
# det s1 co s2 co s3 co iv1
# det co-s1 co-s2 co-s3 iv1
# det s1-co s2-co s3-co iv1
#
# det s1 s2 s3 iv1
#
## Coordination of noun phrases (each group of sentences should have the
## same semantic representation, though with different grammars)
#
# det s1 det s2 co det s3 iv1
# det s1 det s2 det s3 co iv1
#
# det s1 co det s2 co det s3 iv1
# det s1 det s2 co det s3 co iv1
#
# co det s1 co det s2 co det s3 iv1
# det s1 co det s2 co det s3 co iv1
#
# det s1 det s2 det s3 iv1
#
## Coordination of verb phrases (each group of sentences should have the
## same semantic representation, though with different grammars)
#
# det s1 iv1 iv2 co iv3
# det s1 iv1 iv2 iv3 co
#
# det s1 iv1 co iv2 co iv3
# det s1 iv1 iv2 co iv3 co
#
# det s1 co iv1 co iv2 co iv3
# det s1 iv1 co iv2 co iv3 co
#
# det s1 iv1 iv2 iv3
#
## Coordination of sentences
#
# det s1 iv1 det s2 iv2 co det s3 iv3
# det s1 iv1 det s2 iv2 det s3 iv3 co
#
# det s1 iv1 co det s2 iv2 co det s3 iv3
# det s1 iv1 det s2 iv2 co det s3 iv3 co
#
# co det s1 iv1 co det s2 iv2 co det s3 iv3
# det s1 iv1 co det s2 iv2 co det s3 iv3 co
#
# det s1 iv1 det s2 iv2 det s3 iv3
#
# 3. TDL Samples
#
# for an language with a single monosyndeton word-before strategy, we should
# get the following TDL.
#
## mylanguage.tdl:
#
# ;;; Coordination
#
# n1-top-coord-rule := basic-n-top-coord-rule & monopoly-top-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# n1-mid-coord-rule := basic-n-mid-coord-rule & monopoly-mid-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# n1-bottom-coord-rule := conj-first-bottom-coord-rule & n-bottom-coord-phrase &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
#
# np1-top-coord-rule := basic-np-top-coord-rule & monopoly-top-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# np1-mid-coord-rule := basic-np-mid-coord-rule & monopoly-mid-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# np1-bottom-coord-rule := conj-first-bottom-coord-rule & np-bottom-coord-phrase &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
#
# vp1-top-coord-rule := basic-vp-top-coord-rule & monopoly-top-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# vp1-mid-coord-rule := basic-vp-mid-coord-rule & monopoly-mid-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# vp1-bottom-coord-rule := conj-first-bottom-coord-rule & vp-bottom-coord-phrase &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
#
# s1-top-coord-rule := basic-s-top-coord-rule & monopoly-top-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# s1-mid-coord-rule := basic-s-mid-coord-rule & monopoly-mid-coord-rule &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
# s1-bottom-coord-rule := conj-first-bottom-coord-rule & s-bottom-coord-phrase &
#   [ SYNSEM.LOCAL.COORD-STRAT "1" ].
#
## lexicon.tdl:
#
# and_1 := conj-lex &
#   [ STEM < "and" >,
#     SYNSEM.LKEYS.KEYREL.PRED "_and_coord_rel",
#     CFORM "1" ].
#
# 4. Description of cases handled
#
# For the four phrase types N, NP, VP, and S, this module handles every
# combination of the following three dimensions, with a few exceptions
# noted below:
#
# Marking pattern: monosyndeton, polysyndeton, omnisyndeton, asyndeton
# Type of mark: word or affix (with some spelling)
# Position of mark: before or after coordinand
#
# Exceptions: when the pattern is asyndeton, type and position of mark,
# as well as its spelling, must not be specified since they are
# meaningless.  Also, an affix mark can currently only be specified
# for lexical phrase types (i.e. just N).
#
# 5. Known unhandled cases
#
# There are a few coordination strategies that this module cannot encode:
#
# Classical Tibetan and Amharic(Haspelmath 2000):
#   In strategies usually marked A-co B-co C, all but the *first* co
#   can be optionally omitted, giving A-co B C (and so on for N>3).
# Inupiaq (ref?):
#   There is a strategy in this language that is mandatorily bisyndetic
#   when there are two coordinands, but *mandatorily* monosyndetic for
#   3 or more coordinands.  That is, we get A-lu B-lu for two, but
#   A B C-lu for 3 or more.  A-lu B-lu C-lu and A B-lu C-lu are not
#   allowed.
# Indonesian (ref?):
#   A strategy that uses different conjunctions based on position:
#     A B serta C
#     A dan B serta C
#   * A serta B dan C
#   * A serta B serta C
#
# In addition to these, there are some coordination strategies that can
# be implemented using the Matrix rules, but which cannot be described
# with the controls in the web questionnaire.  For example, Hebrew has
# a strategy (ref?) that, like quite a few other strategies including
# Latin -que (ref?), marks the first word of a coordinated phrase.  Such
# a strategy could be implemented by adding a new binary feature, say
# COORDMARKED, that is added by a morphological marking rule and identified
# between all phrases and their first daughters.  Another odd strategy
# is found in Kannada (ref?), where -uu is added to *every word* in a
# coordinated phrase.  The implementation of this would be similar to the
# first-word marking mentioned above, except that the new COORDMARKED
# feature would be identified between phrases and *all* of their daughters.
#
# 6. Description of tdl
#
# For every phrase type that has a coordination strategy, there will be
# a set of rules in mylanguage.tdl created with the same COORD-STRAT value.
# These rules derive from the coordination rules in matrix.tdl (currently
# near tbe bottom of the file), and specify the type of phrase being
# coordinated.  They will have names that begin with the part of speech
# (n, np, vp, s) and the number of the strategy.  For details about the
# implementation, see the comments in matrix.tdl or Drellishak & Bender
# 2005.
#
# 7. Description of customization (python)
#
# The entry point for this code is customize_coordination().  It loops
# through every coordination strategy (currently only 1 and 2).  For each,
# it looks at the user's choices and, from them, constructs a series of
# parameters containing the prefixes and suffixes of the rules that
# will be output (which also determines the prefixes and suffixes of the
# matrix.tdl rules they will derive form.
#
# These are the parameters:
#   num: the number of the strategy
#   pos: the part of speech
#   top: the prefix of the top rule
#   mid: the prefix of the mid rule (empty for poly- and asyndeton)
#   bot: the prefix of the bottom rule
#   left: the prefix of the left rule (only for omnisyndeton)
#   pre: the spelling of the prefix coordination mark (possibly empty)
#   suf: the spelling of the suffix coordination mark (possibly empty)
#
# These parameters are passed to define_coord_strat(), a utility function
# that outputs the actual rules.
#
# 8. Required changes to other modules
#
# None so far.


######################################################################
# define_coord_strat: a utility function, defines a strategy

def define_coord_strat(num, pos, top, mid, bot, left, pre, suf):
  mylang.add_literal(';;; Coordination Strategy ' + num)

  pn = pos + num
  if pos == 'n' or pos == 'np':
    headtype = 'noun'
  else:
    headtype = 'verb'

  # First define the rules in mylang.  Every strategy has a
  # top rule and a bottom rule, but only some have a mid rule, so if
  # the mid prefix argument $mid is empty, don't emit a rule.
  # Similarly, not all strategies have a left rule.

  mylang.add(pn + '-top-coord-rule :=\
               basic-' + pos + '-top-coord-rule &\
               ' + top + 'top-coord-rule &\
               [ SYNSEM.LOCAL.COORD-STRAT "' + num + '" ].')
  if mid:
    mylang.add(pn + '-mid-coord-rule :=\
                 basic-' + pos + '-mid-coord-rule &\
                 ' + mid + 'mid-coord-rule &\
                 [ SYNSEM.LOCAL.COORD-STRAT "' + num + '" ].')

  if pre or suf:
    # first the rule in mylang
    mylang.add(pn + '-bottom-coord-rule :=\
               ' + bot + 'bottom-coord-rule &\
               [ SYNSEM.LOCAL.COORD-STRAT "' + num + '",\
                 SYNSEM.LOCAL.COORD-REL.PRED "_and_coord_rel",\
                 DTR.SYNSEM.LOCAL.CAT.HEAD ' + headtype + ' ].')

    # now the spelling change rule in irules.tdl
    rule = pn + '-bottom :=\n'
    if pre:
      rule += '  %prefix (* ' + pre + ')\n'
    else:
      rule += '  %suffix (* ' + suf + ')\n'
    rule += '  ' + pn + '-bottom-coord-rule.'
    irules.add_literal(rule)
  else:
    rule = pn + '-bottom-coord-rule :=\
           ' + bot + 'bottom-coord-rule &\
           ' + pos + '-bottom-coord-phrase &\
           [ SYNSEM.LOCAL.COORD-STRAT "' + num + '" ].'
    mylang.add(rule)
    if bot == 'unary-':
      rule = pn + '-bottom-coord-rule :=\
             [ SYNSEM.LOCAL.COORD-REL.PRED "_and_coord_rel" ].'
      mylang.add(rule)

  if left:
    # first the rule in mylang
    rule = pn + '-left-coord-rule :=\
           ' + bot + 'left-coord-rule &\
           ' + pos + '-bottom-coord-phrase.'
    mylang.add(rule)

    if pre or suf:
      # constrain the predicate
      mylang.add(pn + '-left-coord-rule :=\
                 [ SYNSEM.LOCAL.COORD-REL.PRED "_and_coord_rel" ].')

      # now the spelling change rule in irules.tdl
      rule = pn + '-left :=\n'
      if pre:
        rule += '  %prefix (* ' + pre + ')\n'
      else:
        rule += '  %suffix (* ' + suf + ')\n'
      rule += '  ' + pn + '-left-coord-rule.'
      irules.add_literal(rule)

  # Now define the rule instances into rules.tdl.  As above, the mid
  # or left rule may not be necessary.

  rules.add(pn + '-top-coord := ' + pn + '-top-coord-rule.')
  if mid:
    rules.add(pn + '-mid-coord := ' + pn + '-mid-coord-rule.')
  rules.add(pn + '-bottom-coord := ' + pn + '-bottom-coord-rule.')
  if left:
    rules.add(pn + '-left-coord := ' + pn + '-left-coord-rule.')


######################################################################
# customize_coordination(): the main coordination customization routine

def customize_coordination():
  i = 0
  ch.iter_begin('cs')
  while ch.iter_valid():
    i += 1

    mark = ch.get('mark')
    pat = ch.get('pat')
    orth = ch.get('orth')
    order = ch.get('order')

    pre = ''
    suf = ''

    if mark == 'word':
      lexicon.add(TDLencode(orth) + ' := conj-lex &\
                  [ STEM < "' + orth + '" >,\
                    SYNSEM.LKEYS.KEYREL.PRED "_and_coord_rel",\
                    CFORM "' + str(i) + '" ].')
      if pat == 'omni':
        lexicon.add(TDLencode(orth) + '_nosem := nosem-conj-lex &\
                      [ STEM < "' + orth + '" >,\
                        CFORM "' + str(i) + '" ].')

    if pat == 'a':
      top = 'apoly-'
      mid = ''
      bot = 'unary-'
      left = ''
    else:
      if pat == 'mono':
        top = 'monopoly-'
        mid = 'monopoly-'
        bot = ''
        left = ''
      elif pat == 'omni':
        top = 'omni-'
        mid = 'omni-'
        bot = 'omni-'
        left = 'omni-'
      elif pat == 'poly':
        top = 'apoly-'
        mid = ''
        bot = ''
        left = ''

      if mark == 'affix':
        bot = 'infl-'
        if order == 'before':
          pre = orth
        else:
          suf = orth
      else:
        if order == 'before':
          bot += 'conj-first-'
          if left:
            left += 'conj-first-'
        else:
          bot += 'conj-last-'
          if left:
            left += 'conj-last-'

    for pos in ('n', 'np', 'vp', 's'):
      if ch.get(pos):
        define_coord_strat(str(i), pos, top, mid, bot, left, pre, suf)

    ch.iter_next()
  ch.iter_end()


######################################################################
# customize_yesno_questions()
#   Create the type definitions associated with the user's choices
#   about matrix yes/no questions.

# DOCUMENTATION

# 2. Seed strings, requirements of POS lexicon:

# The only addition to the POS lexicon is qpart, the question particle:
# Also -ques|ques- the affix

# qpart
# -ques
# ques-

# The seed strings are written assuming an SVO language with no
# adpositions (in order to illustrate inversion).  Again all the
# seed strings have the same semantics, modulo determiners.  For
# the purposes of harvesting the semantics, I recommend these two
# strings, parsed with an SOV grammar which expresses yes no questions
# with a sentence final question particle:

# s o tv qpart
# det s det o tv qpart

# Now the SVO seed strings:

# s tv o qpart
# tv s o
# aux s tv o

# det s tv det o qpart
# tv det s det o
# aux det s tv det o

# s tv-ques o
# s ques-tv o
# s aux-ques tv o
# s ques-aux tv o

# det s tv-ques det o
# det s ques-tv det o
# det s aux-ques tv det o
# det s ques-aux tv det o

# Since this module actually involves changes to word order, the
# seed strings/permutation interaction is actually different.  I
# think it will come down to being careful with the filters...

# Note also that the semantic contrast between questions and non-questions
# is that questions are marked as [ MESG ques ] while non-questions are
# [ MESG prop-or-ques ].  The type prop-or-ques subsumes ques, but
# in [incr tsdb()], we'll be looking at exact match semantics, not
# unification or other measures of compatibility.

# 8. Changes to other modules:

# Moving to the complementizer analysis of question particles impacted
# the word order module.  In particular, we now have to worry about
# the order of question particles with respect to heads when we do the
# head-comp and comp-head rules, just like we have to worry about the
# adpositions.  I also had to touch the root definition, to allow for
# CPs as roots.

def customize_yesno_questions():

  qinvverb = ch.get('q-inv-verb')
  qpartposthead = ch.get('q-part-order')
  qpartform = ch.get('q-part-orth')

  if ch.get('q-inv'):
    comment = \
      'For the analysis of inverted yes-no questions, we add the feature INV.'
    mylang.add('verb :+ [ INV bool ].', comment)

    comment = \
      'All verbs start off as not inverted.'
    mylang.add('verb-lex := [ SYNSEM.LOCAL.CAT.HEAD.INV - ].', comment)


    comment = \
      'Rule for inverted subject verb order in questions.\n' + \
      'The incompatible SUBJ values on SYNSEM and DTR are\n' + \
      'what keeps this one from spinning.'
    if qinvverb == 'aux':
      aux = ', AUX +'
    elif qinvverb == 'main':
      aux = ', AUX -'
    elif qinvverb == 'main-aux':
      aux = ''
      # ERB 2006-10-05 Adding in semantics here.  This rule constrains MESG to ques.
      # ERB 2007-01-21 Removing semantics here: Need to allow inversion to not express questions.  Instead, the result of this is MC na, and there is a separate non-branching rule which introduces question semantics.  Following the ERG in this.
    typedef = '''
    subj-v-inv-lrule := cat-change-only-lex-rule &
			same-hc-light-lex-rule &
			same-posthead-lex-rule &
                        constant-lex-rule &
      [ SYNSEM [ LOCAL.CAT [ HEAD verb & [ INV +''' + aux + ''' ],
                             VAL [ COMPS < #subj . #comps >,
                                     SUBJ < >,
                                     SPR #spr,
                                     SPEC #spec ],
                             MC na ],
                 LKEYS #lkeys ],
        DTR.SYNSEM [ LOCAL.CAT.VAL [ SUBJ < #subj >,
                                     COMPS #comps,
                                     SPR #spr,
                                     SPEC #spec ],
                     LKEYS #lkeys ]].'''
    mylang.add(typedef, comment)

    lrules.add('inv-lr := subj-v-inv-lrule.')

    # ERB 2007-01-21 Then we need the non-branching construction which
    # corrects to MC + and adds SF ques.

    comment = \
           'This rule takes [MC na] inverted phrases and licneses' + \
           'them as main clauses with question semantics.\n'

    typedef = '''
    int-cl := interrogative-clause & head-only &
    [ SYNSEM.LOCAL.CAT [ HEAD.INV +,
                         VAL #val,
                         MC + ],
      HEAD-DTR.SYNSEM.LOCAL.CAT [ MC na,
                                  VAL #val &
                                       [SUBJ < >,
                                       COMPS < >]],
      C-CONT.HOOK.INDEX.SF ques ].'''
    mylang.add(typedef, comment)

    rules.add('int := int-cl.')

  # ERB 2006-10-05 Moving away from the modifier analysis of question particles
  # which I think doesn't handle the facts well.  These look more like complementizers
  # to me.

  if ch.get('q-part'):
    comment = \
             'We treat question particles as complementizers.\n' + \
             'Here is the lexical type for complementizers.'
    typedef = '''
      complementizer-lex-item := raise-sem-lex-item & basic-one-arg &
         [ SYNSEM.LOCAL.CAT [ HEAD comp &
                                   [ MOD < > ],
                              VAL [ SPR < >,
                                    SUBJ < >,
                                    COMPS < #comp > ]],
           ARG-ST < #comp & [ LOCAL.CAT [ MC +,
                                          HEAD verb,
                                          VAL [ SUBJ < >,
                                                COMPS < > ]]] > ]
                                                .'''
    mylang.add(typedef,comment)

    comment = 'Subtype for question particles. Constrains SF to ques.'
    typedef = '''
      qpart-lex-item := complementizer-lex-item &
         [ SYNSEM.LOCAL.CONT.HOOK.INDEX.SF ques ].'''
    mylang.add(typedef,comment)

  if ch.get('q-infl'):

    mylang.add('ques-infl-lex-rule := add-only-no-ccont-rule & inflecting-lex-rule &\
    [ SYNSEM.LOCAL.CONT.HOOK.INDEX.SF ques,\
    DTR lex-item & [ SYNSEM.LOCAL.CAT.HEAD verb ]].',
               'Constrains SF to ques. Instantiated by a verbal affix.')

    if ch.get('q-infl-type') == 'aux':
      mylang.add('ques-infl-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX + ].',
                 'This rule applies only to auxiliaries.')

    if ch.get('q-infl-type') == 'main' and has_auxiliaries_p():
      mylang.add('ques-infl-lex-rule := [ DTR.SYNSEM.LOCAL.CAT.HEAD.AUX - ].',
                 'This rule applies only to main verbs.')


    add_irule('ques-infl-lr','ques-infl-lex-rule',ch.get('ques-aff'),ch.get('ques-aff-orth'))


######################################################################
# customize_arg_op()
#   Create phrase-structure and lexical rules associated with user's
#   choices on argument optionality page.

def customize_arg_op():
  """ Create the lexical types, lexical, rules and phrase structure
      rules to allow argument dropping"""
  #Figure out the constraints on subject dropping and write the 
  #appropriate types to mylang.tdl or rules.tdl

  if ch.get('subj-drop') == 'subj-drop-all':
    rules.add('decl-head-opt-subj := decl-head-opt-subj-phrase.') 
  if ch.get('subj-drop') == 'subj-drop-lex':
    rules.add('decl-head-opt-subj := decl-head-opt-subj-phrase.')
    mylang.add('no-subj-drop-verb-lex := verb-lex &\
                         [SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT -].')
    mylang.add('subj-drop-verb-lex := verb-lex.')
  

  #Figure out the constraints on object dropping and write the 
  #appropriate types to mylang.tdl or rules.tdl
  if ch.get('obj-drop')=='obj-drop-all':
    rules.add('basic-head-opt-comp := basic-head-opt-comp-phrase.')

  if ch.get('obj-drop') == 'obj-drop-lex':
    rules.add('basic-head-opt-comp := basic-head-opt-comp-phrase.')
    mylang.add('no-obj-drop-verb-lex := transitive-verb-lex &\
                        [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].')
    mylang.add('obj-drop-verb-lex := transitive-verb-lex.')

  if ch.get('subj-drop') == 'subj-drop-lex' and ch.get('obj-drop') == 'obj-drop-lex':
    mylang.add('subj-drop-only-verb-lex := subj-drop-verb-lex & no-obj-drop-verb-lex.')
    mylang.add('obj-drop-only-verb-lex := obj-drop-verb-lex & no-subj-drop-verb-lex.')
    mylang.add('subj-obj-drop-verb-lex := subj-drop-verb-lex & obj-drop-verb-lex.')
    mylang.add('no-drop-verb-lex := no-subj-drop-verb-lex & no-obj-drop-verb-lex.')


  #Create phrase-structure rules for each context
  ch.iter_begin('context')
  i=1
  while ch.iter_valid():
    name = 'context' + str(i)
    ptype = name + '-decl-head-opt-subj-phrase'
    customize_feature_values(ptype, 'verb')
    typedef = ptype + ':= decl-head-opt-subj-phrase.'
    mylang.add(typedef)
    rules.add(name + '-decl-head-opt-subj := '+ name + '-decl-head-opt-subj-phrase.')
    i = i+1
    ch.iter_next()
  ch.iter_end()

  #Trying to get co-occurrence of marker dropping to work

  if (ch.get('subj-mark-no-drop') == 'subj-mark-no-drop-not' and (ch.get('subj-mark-drop')== 'subj-mark-drop-opt'or ch.get('subj-mark-drop')=='subj-mark-drop-req')):
    mylang.add( 'basic-head-subj-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT -].', merge = True)

  if ch.get('obj-drop')=='obj-drop-all' and ((ch.get('obj-mark-no-drop') == 'obj-mark-no-drop-not' and ch.get('obj-mark-drop') == 'obj-mark-drop-req') or ((ch.get('obj-mark-no-drop') == 'obj-mark-no-drop-opt' and ch.get('obj-mark-drop') == 'obj-mark-drop-req'))):
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

  if ch.get('obj-mark-no-drop') == 'obj-mark-no-drop-not' and ch.get('obj-mark-drop') == 'obj-mark-drop-opt' :
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

  if ch.get('obj-mark-no-drop') == 'obj-mark-no-drop-req' and ch.get('obj-mark-drop') == 'obj-mark-drop-not' :
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

  if ch.get('obj-mark-no-drop') == 'obj-mark-no-drop-opt' and ch.get('obj-mark-drop') == 'obj-mark-drop-not' :
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

  if ch.get('obj-mark-drop')== 'obj-mark-drop-opt' and ch.get_full('obj-mark-no-drop') == 'obj-mark-no-drop-req':
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

  if ch.get('subj-mark-drop')== 'subj-mark-drop-opt' and ch.get_full('subj-mark-no-drop') == 'subj-mark-no-drop-req':
    mylang.add( 'basic-head-comp-phrase :+ [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT -].', merge = True)

#def customize_subj_phrase(phrase)
  #Trying to get the subject/object marker co-occurrence to work out
  #if (ch.get('subj-mark-no-drop') == 'subj-mark-no-drop-not' and (ch.get('subj-mark-drop')== 'subj-mark-drop-opt'or ch.get('subj-mark-drop')=='subj-mark-drop-req')):
   # mylang.add(phrase + ':= [HEAD-DTR.SYNSEM.LOCAL.CAT.VAL.SUBJ.FIRST.OPT +].', merge = True)

######################################################################
# customize_lexicon()
#   Create the type definitions associated with the user's test
#   lexicon.

def customize_nouns():
  # Figure out which kinds of determiner-marking are in the language
  seen = {'obl':False, 'opt':False, 'imp':False}
  seenCount = 0

  ch.iter_begin('noun')
  while ch.iter_valid():
    det = ch.get('det')
    if not seen[det]:
      seen[det] = True
      seenCount += 1
    ch.iter_next()
  ch.iter_end()

  singlentype = (seenCount == 1)

  # Add the lexical types to mylang
  mylang.add_literal(';;; Lexical types')

  # Lexical types for nouns
  mylang.add_literal(';;; Nouns')

  # Playing fast and loose with the meaning of OPT on SPR.  Using
  # OPT - to mean obligatory (as usual), OPT + to mean impossible (that's
  # weird), and leaving OPT unspecified for truly optional.  Hoping
  # this will work at least for LSA111 lab.

  # ERB 2006-11-28 Update: To make that weird use of OPT work, the
  # head-spec rule has to require [OPT -] on its non-head daughter.
  # Adding that just in case we add the no-spr-noun-lex type.

  typedef = \
    'noun-lex := basic-noun-lex & basic-one-arg & no-hcons-lex-item & \
       [ SYNSEM.LOCAL [ CAT.VAL [ SPR < #spr & [ LOCAL.CAT.HEAD det ] >, \
                                  COMPS < >, \
                                  SUBJ < >, \
                                  SPEC < > ] ], \
         ARG-ST < #spr > ].'
  mylang.add(typedef)

  if singlentype:
    if seen['obl']:
      typedef = 'noun-lex := [ SYNSEM.LOCAL.CAT.VAL.SPR < [ OPT - ] > ].'
      mylang.add(typedef)
    elif seen['imp']:
      typedef = 'noun-lex := [ SYNSEM.LOCAL.CAT.VAL.SPR < [ OPT + ] > ].'
      mylang.add(typedef)
  else:
    if seen['obl']:
      typedef = \
        'obl-spr-noun-lex := noun-lex & \
           [ SYNSEM.LOCAL.CAT.VAL.SPR < [ OPT - ] > ].'
      mylang.add(typedef)

    if seen['imp']:
      typedef = \
        'no-spr-noun-lex := noun-lex & \
           [ SYNSEM.LOCAL.CAT.VAL.SPR < [ OPT + ] > ].'
      mylang.add(typedef)

  if seen['imp'] and ch.get('has-dets') == 'yes':
    mylang.add(
      'head-spec-phrase := [ NON-HEAD-DTR.SYNSEM.OPT - ].',
      'Nouns which cannot take specifiers mark their SPR requirement\n' +
      'as OPT +.  Making the non-head daughter OPT - in this rule\n' +
      'keeps such nouns out.')

  if ch.get('case-marking') != 'none':
    if not ch.has_adp_case():
      mylang.add('noun :+ [ CASE case ].')

  # Add the lexical entries
  lexicon.add_literal(';;; Nouns')

  ch.iter_begin('noun')
  while ch.iter_valid():
    name = get_name()
    det = ch.get('det')

    if singlentype or det == 'opt':
      stype = 'noun-lex'
    elif det == 'obl':
      stype = 'obl-spr-noun-lex'
    else:
      stype = 'no-spr-noun-lex'

    ntype = name + '-noun-lex'

    mylang.add(ntype + ' := ' + stype + '.')

    customize_feature_values(ntype, 'noun')

    ch.iter_begin('stem')
    while ch.iter_valid():
      orth = ch.get('orth')
      pred = ch.get('pred')
      typedef = TDLencode(orth) + ' := ' + ntype + ' & \
                  [ STEM < "' + orth + '" >, \
                    SYNSEM.LKEYS.KEYREL.PRED "' + pred + '" ].'
      lexicon.add(typedef)

      ch.iter_next()
    ch.iter_end()

    ch.iter_next()
  ch.iter_end()

# Given the canonical (i.e. choices variable) name of a case, return
# its abbreviation from the list of cases, which should be created by
# calling ChoicesFile.cases().  If there is no abbreviation, return
# the name.
def canon_to_abbr(name, cases):
  for c in cases:
    if c[0] == name:
      return c[2]
  return name


# Given the name of a case, return its abbreviation from the list of
# cases, which should be created by calling ChoicesFile.cases().  If
# there is no abbreviation, return the name.
def name_to_abbr(name, cases):
  for c in cases:
    if c[1] == name:
      return c[2]
  return name


def customize_verb_case():
  cm = ch.get('case-marking')
  cases = ch.cases()

  # Pass through the list of case-marking patterns.  If a pattern is a
  # lexical pattern (i.e. the third item in the list is False), then
  # create and contrain the appropriate lexical type.  This type is a
  # subtype of either transitive-verb-lex or intransitive-verb-lex.
  #
  # Note: I specify ARG-ST.FIRST... below instead of ARG-ST < [], ...>
  # because TDLFile has trouble with merges and open-ended lists.
  # Which should get fixed...  - sfd

  for p in ch.patterns():
    rule_pattern = p[2]

    p = p[0].split(',')  # split off ',dirinv', if present
    dir_inv = ''
    if len(p) > 1 and p[1] == 'dirinv':
      dir_inv = 'dir-inv-'

    if not rule_pattern:
      c = p[0].split('-')  # split 'agentcase-patientcase'
      if p[0] == 'trans' or len(c) > 1:  # transitive
        if p[0] == 'trans':
          a_case = ''
          o_case = ''
          a_head = ch.case_head()
          o_head = ch.case_head()
        else:
          a_case = canon_to_abbr(c[0], cases)
          o_case = canon_to_abbr(c[1], cases)
          a_head = ch.case_head(c[0])
          o_head = ch.case_head(c[1])

        if a_case and o_case:
          t_type = dir_inv + a_case + '-' + o_case + '-transitive-verb-lex'
        else:
          t_type = dir_inv + 'transitive-verb-lex'

        if t_type != 'transitive-verb-lex':
          mylang.add(t_type + ' := transitive-verb-lex.')

        # constrain the head of the agent/subject
        typedef = \
          t_type + ' := \
          [ ARG-ST.FIRST.LOCAL.CAT.HEAD ' + a_head + ' ].'
        mylang.add(typedef)

        # constrain the case of the agent/subject
        if a_case:
          typedef = \
            t_type + ' := \
            [ ARG-ST.FIRST.LOCAL.CAT.HEAD.CASE ' + a_case + ' ].'
          mylang.add(typedef)

        # constrain the head of the patient/object
        typedef = \
          t_type + ' := \
          [ ARG-ST < [ ], [ LOCAL.CAT.HEAD ' + o_head + ' ] > ].'
        mylang.add(typedef)

        # constrain the case of the patient/object
        if o_case:
          typedef = \
            t_type + ' := \
            [ ARG-ST < [ ], [ LOCAL.CAT.HEAD.CASE ' + o_case + ' ] > ].'
          mylang.add(typedef)
      else:     # intransitive
        if c[0] == 'intrans':
          s_case = ''
          s_head = ch.case_head()
        else:
          s_case = canon_to_abbr(c[0], cases)
          s_head = ch.case_head(c[0])

        if s_case:
          i_type = dir_inv + s_case + '-intransitive-verb-lex'
        else:
          i_type = dir_inv + 'intransitive-verb-lex'

        if i_type != 'intransitive-verb-lex':
          mylang.add(i_type + ' := intransitive-verb-lex.')

        # constrain the head of the subject
        typedef = \
          i_type + ' := \
          [ ARG-ST.FIRST.LOCAL.CAT.HEAD ' + s_head + ' ].'
        mylang.add(typedef)

        # constrain the case of the subject
        if s_case:
          typedef = \
            i_type + ' := \
            [ ARG-ST.FIRST.LOCAL.CAT.HEAD.CASE ' + s_case + ' ].'
          mylang.add(typedef)


###############################################################
# customize_form()
 
def init_form_hierarchy():
  """
  Create the FORM hierarchies associated with the user's choices
  about verb forms
  Adds FORM finite and nonfinte values if there are auxiliaries 
  or if user specified
  """
  hier = Hierarchy('form')

  if has_auxiliaries_p() or ch.is_set_full('noaux-fin-nf'):

    hier.add('nonfinite', 'form')
    hier.add('finite', 'form')

    for p in ('nf', 'fin'):

      ch.iter_begin(p + '-subform')
      while ch.iter_valid():

        if p == 'nf':
          super = 'nonfinite'
        elif p == 'fin':
          super = 'finite'

        sub = ch.get('name')
        hier.add(sub, super)

        ch.iter_next()
      ch.iter_end()

  if not hier.is_empty():
    hierarchies[hier.name] = hier


def customize_form():
  if 'form' in hierarchies:
    mylang.add('head :+ [FORM form].')
    hierarchies['form'].save(mylang)


##########################################################
# customize_verbs()

def customize_verbs():
  negmod = ch.get('neg-mod')
  negadv = ch.get('neg-adv')
  wo = ch.get('word-order')  
  auxcomp = ch.get('aux-comp')
  
  # Do we need to constrain HC-LIGHT on verbs, to distinguish V from VP?
  hclight = (negadv == 'ind-adv' and negmod == 'v')
  hclightallverbs = False

  vc = ch.get('v-cluster')
  if has_auxiliaries_p():
    if wo == 'vso' or wo == 'osv':
      wo = 'req-hcl-vp'
    if auxcomp == 'v' and hclight != True:
      hclight = True
      if wo != 'free' or vc == 'yes':
        hclightallverbs = True
    if auxcomp == 'vp' and wo == 'req-hcl-vp':
      hclightallverbs = True
  
  if wo == 'req-hcl-vp':
    wo = ch.get('word-order')

  # Lexical types for verbs
  # I'm adding the constraint to associate XARG with the
  # first ARG-ST element here (so raising auxiliaries work),
  # but perhaps this belongs in matrix.tdl?  Or maybe this
  # is another module/parameter (like, the external argument
  # might not be the first one?

  mylang.add_literal(';;; Verbs')

  mainorverbtype = main_or_verb() 
# The variable mainorverbtype is a type name for lexical/main (non-aux) verbs.
# Note that the use of 'main' instead of 'lexical' is strictly for 
# coding clarity 
# If there are auxiliaries, non-aux verbs are 'main-verb-lex', and 'verb-lex'
# includes both aux and lexical/main verbs.
# If there are no auxiliaries then 'verb-lex' covers all verbs
  
  if has_auxiliaries_p():
    mylang.add('head :+ [ AUX bool ].')
    #mainorverbtype = 'main-verb-lex'
     
# we need to know whether the auxiliaries form a vcluster

    auxorder = ch.get('aux-comp-order')    
    vcluster = determine_vcluster(auxcomp, auxorder, wo)

    typedef = \
      'verb-lex := lex-item & \
                 [ SYNSEM.LOCAL.CAT.HEAD verb ].'
    mylang.add(typedef)
    typedef = \
      'main-verb-lex := verb-lex & basic-verb-lex & \
                      [ SYNSEM.LOCAL.CAT.HEAD.AUX - ].'
    mylang.add(typedef)
    typedef = \
      'aux-lex := verb-lex & \
                [ SYNSEM.LOCAL.CAT.HEAD.AUX + ].'
    mylang.add(typedef)
    if vcluster:
      mylang.add('main-verb-lex := [ SYNSEM.VERB-CL + ].')
      mylang.add('aux-lex := [ SYNSEM.VERB-CL - ].')
  else:
    #mainorverbtype = 'verb-lex'
    mylang.add('verb-lex := basic-verb-lex.')

  typedef = mainorverbtype + ' :=  \
       [ SYNSEM.LOCAL [ CAT.VAL [ SPR < >, \
                                  SPEC < >, \
                                  SUBJ < #subj > ], \
                        CONT.HOOK.XARG #xarg ], \
         ARG-ST < #subj & \
                  [ LOCAL [ CAT.VAL [ SPR < >, \
                                      COMPS < > ], \
                            CONT.HOOK.INDEX #xarg ] ], ... > ].'
  mylang.add(typedef)
  
  if hclightallverbs:
    mylang.add('verb-lex := [ SYNSEM.LOCAL.CAT.HC-LIGHT - ].')  
  elif hclight:
    comment = \
      ';;; If there are aspects of the syntax which pick out\n' + \
      ';;; lexical Vs (transitive or intransitive) such as V-attachment\n' + \
      ';;; of adverbs or argument composition auxiliaries which take V\n' + \
      ';;; complements, we need to distinguish (intranstive) V and VP.\n' + \
      ';;; To do so, we make use of a feature LIGHT.  Phrases are\n' + \
      ';;; generally [LIGHT -] with the exception of head-complement\n' + \
      ';;; phrases, which take their value for LIGHT from the head\'s\n' + \
      ';;; HC-LIGHT feature.  To make this work for us here, constraint\n' + \
      ';;; HC-LIGHT on verbs to be -.'
#    mylang.add_literal(comment)
    mylang.add(mainorverbtype + ' := [ SYNSEM.LOCAL.CAT.HC-LIGHT - ].')

  # intransitive verb lexical type
  typedef = \
    'intransitive-verb-lex := ' + mainorverbtype + ' & intransitive-lex-item & \
       [ SYNSEM.LOCAL.CAT.VAL.COMPS < > ].'
  mylang.add(typedef)

  # transitive verb lexical type
  typedef = \
    'transitive-verb-lex := ' + mainorverbtype + ' & transitive-lex-item & \
       [ SYNSEM.LOCAL.CAT.VAL.COMPS < #comps >, \
         ARG-ST < [ ], \
                  #comps & \
                  [ LOCAL.CAT [ VAL [ SPR < >, \
                                      COMPS < > ] ] ] > ].'
  mylang.add(typedef)

  customize_verb_case()

  # Lexical entries
  lexicon.add_literal(';;; Verbs')

  # Now create the lexical entries for all the defined verb types
  cases = ch.cases()
  ch.iter_begin('verb')
  while ch.iter_valid():
    name = get_name()
    val = ch.get('valence')
    

    i = val.find(',')
    dir_inv = ''
    if i != -1:
      val = val[:i]
      dir_inv = 'dir-inv-'

    if val == 'trans':
      tivity = 'trans'
    elif val == 'intrans':
      tivity = 'intrans'
    elif val.find('-') != -1:
      c = val.split('-')
      a_case = canon_to_abbr(c[0], cases)
      o_case = canon_to_abbr(c[1], cases)
      tivity = a_case + '-' + o_case + '-trans'
    else:
      s_case = canon_to_abbr(val, cases)
      tivity = s_case + '-intrans'
    
    stype = dir_inv + tivity + 'itive-verb-lex'
    vtype = name + '-verb-lex'

    mylang.add(vtype + ' := ' + stype + '.')

    customize_feature_values(vtype, 'verb', None, cases)

    ch.iter_begin('stem')
    while ch.iter_valid():
      orth = ch.get('orth')
      pred = ch.get('pred')
      typedef = \
        TDLencode(orth) + ' := ' + vtype + ' & \
                    [ STEM < "' + orth + '" >, \
                      SYNSEM.LKEYS.KEYREL.PRED "' + pred + '" ].'
      lexicon.add(typedef)

      ch.iter_next()
    ch.iter_end()

    ch.iter_next()
  ch.iter_end()



#######################################################
def customize_users_auxtype(userstype, supertype):
  """
  A utility that declares the userstype as subtype of supertype and 
  calls the functions that specify feature values on the type.
  Called by customize_auxiliaries.
  userstype = userstypename in customize_auxiliaries
  supertype = userstypename in customize_auxiliaries
  """
 
  customize_feature_values(userstype, 'aux')
  customize_feature_values(userstype, 'auxcomplement')
  mylang.add(userstype + ' := ' + supertype + '.') 


def add_subj_tdl(type, subj, subjcase):
  """
  A function to add subject related tdl to type definition if the complement
  is either a V or a VP.
  Called by customize_auxiliaries().
  type = supertype variable in customize_auxiliaries()
  subj = subj variable in customize_auxiliaries()
  """
  if subj == 'adp':
    mylang.add(type + ' := [ ARG-ST.FIRST.LOCAL.CAT.HEAD adp ].')
  else:
    mylang.add(type + ' := [ ARG-ST.FIRST.LOCAL.CAT.HEAD noun ].')
    if subj == 'np-comp-case':
      mylang.add(type + ' := [ ARG-ST < [ LOCAL.CAT.HEAD.CASE #case  ], \
                                        [ LOCAL.CAT.VAL.SUBJ < [ LOCAL.CAT.HEAD.CASE #case ] > ] > ].')
    elif subj == 'np-aux-case': 
      mylang.add(type + ' := [ ARG-ST.FIRST.LOCAL.CAT.HEAD.CASE ' + subjcase + ' ].')

def get_auxtypename(sem, supertype):
  """
  A function that creates the auxiliary type name.
  sem = sem variable from customize_auxiliaries()
  supertype = supertype variable from customize_auxiliaries()
  """
  if sem == 'add-pred':
    auxtypename = supertype + '-with-pred'
  else:
    auxtypename = supertype + '-no-pred'
  return auxtypename

def customize_auxiliaries():

  if has_auxiliaries_p():
    mylang.add_literal(';;; Auxiliaries')
    lexicon.add_literal(';;; Auxiliaries')
    comp = ch.get('aux-comp')
    wo = ch.get('word-order')
    vc = ch.get('v-cluster')

    ch.iter_begin('aux')
    while ch.iter_valid():
      name = ch.get('name')
      userstypename = name + '-aux-lex'      
      sem = ch.get('sem')
      subj = ch.get('subj')
      subjc = ch.get('subj_case') 
      cases = ch.cases()
      subjcase = canon_to_abbr(subjc, cases)      

    # Lexical type for auxiliaries.
    # ASF 2008-11-25 added constraints SS.LOC.CONT.HOOK.XARG #xarg and 
    # ARG-ST.FIRST.LOCAL.CONT.HOOK.INDEX #xarg for subj-raise-aux and 
    # arg-comp-aux, to insure the subject is passed up when several auxs are 
    # present in sentence. Implemented here, because it required least changes
    # it may be cleaner to have this in general verb-lex, as well as the first
    # ARG is #subj constraint (but not possible for aux with s-comp)

      if comp == 'vp':
        supertype = 'subj-raise-aux'
        auxtypename = get_auxtypename(sem, supertype)

        typedef = supertype + ' := aux-lex & trans-first-arg-raising-lex-item  & \
                   [ SYNSEM.LOCAL [ CAT.VAL [ SUBJ < #subj >, \
                                            COMPS < #comps >, \
                                            SPR < >, \
                                            SPEC < > ], \
                                    CONT.HOOK.XARG #xarg ], \
                     ARG-ST < #subj & \
                              [ LOCAL [ CAT.VAL [ SPR < >, \
                                                  COMPS < > ],\
                                        CONT.HOOK.INDEX #xarg ] ], \
                              #comps & \
                              [ LOCAL.CAT [ VAL [ SUBJ < [ ] >, \
                                                  COMPS < > ], \
                                            HEAD verb ]] > ].'
        mylang.add(typedef)        
        add_subj_tdl(supertype, subj, subjcase)

        if sem == 'add-pred':
          typedef = auxtypename + ' := ' + supertype + ' & norm-sem-lex-item & \
                                        trans-first-arg-raising-lex-item-1 .'
          mylang.add(typedef)

        else:
          comment = \
            '; To keep the semantically empty ones from spinning on\n' + \
            '; generation, require complement to be [AUX -].  The\n' + \
            '; FORM feature might be enough in the starter grammars,\n' + \
            '; but I don\'t want to rely on this.  Then again, [ AUX - ]\n' + \
            '; might not be true.  Be sure to put in a comment.'
          mylang.add_literal(comment)
          # changed inheritance here to remove redundancy
          typedef = auxtypename + ' := ' + supertype + ' & raise-sem-lex-item & \
                      [ ARG-ST < [ ], [ LOCAL.CAT.HEAD.AUX - ] > ].'
          mylang.add(typedef)
        
        customize_users_auxtype(userstypename, auxtypename)

      elif comp == 'v':
        supertype = 'arg-comp-aux'
        auxtypename = get_auxtypename(sem, supertype) 
        comment = \
          '; Somewhat surprisingly, this inherits from basic-two-arg, so\n' + \
          '; that the non-local features are amalgamated from subj, the\n' + \
          '; lexical verb complement, but not the other complements, if any.'
        mylang.add_literal(comment)
        
        typedef = supertype + ' := aux-lex & basic-two-arg & \
             [ SYNSEM.LOCAL [ CAT.VAL [ SUBJ < #subj  >, \
                                      COMPS < #comps . #vcomps >, \
                                      SPR < >, \
                                      SPEC < > ], \
                              CONT.HOOK.XARG #xarg ], \
               ARG-ST < #subj & \
                        [ LOCAL [ CAT [ VAL [ SPR < >, \
                                              COMPS < > ]], \
                                  CONT.HOOK.INDEX #xarg ]], \
                      #comps & \
                      [ LIGHT +, \
                        LOCAL [ CAT [ VAL [ SUBJ < [ ] >, \
                                            COMPS #vcomps ], \
                                      HEAD verb ], \
                                CONT.HOOK.XARG #xarg ]] > ].'
        mylang.add(typedef)      
        add_subj_tdl(supertype, subj, subjcase)

# ASF 2008-12-07 For now we restrict free word order with v-comp to
# either verbal clusters or one auxiliary max
      
        if wo == 'free' and vc == 'no':
          mylang.add(supertype + ' := [ ARG-ST < [ ], [ LOCAL.CAT.HEAD.AUX - ] > ].')
         
        if sem == 'add-pred':
          comment = \
            '; Not inheriting from basic-verb-lex, so need to put in\n' + \
            '; event-relation by hand here.'
          mylang.add_literal(comment)

          typedef = auxtypename + ' := ' + supertype + ' & hcons-lex-item & \
               [ SYNSEM [ LOCAL [ CONT.HCONS <! qeq & \
                                                [ HARG #harg, \
                                                  LARG #larg ] !> ], \
                          LKEYS.KEYREL event-relation & \
                                       [ ARG1 #harg ]], \
                 ARG-ST < [ ], [ LOCAL.CONT.HOOK.LTOP #larg ] > ].'
          mylang.add(typedef)

        else:
          comment = \
            '; Note that raise-sem-lex-item assumes the first complement is\n' + \
            '; where the HOOK comes from.  It\'s not clear to me how you\'d\n' + \
            '; tell that you had an argument composition auxiliary if it\n' + \
            '; wasn\'t appearing adjacent to the verb.'
          mylang.add_literal(comment)

          typedef = auxtypename + ' := ' + supertype + '  & raise-sem-lex-item & \
               [ ARG-ST < [ ], [ LOCAL.CAT.HEAD.AUX - ] > ].'
          mylang.add(typedef)

        customize_users_auxtype(userstypename, auxtypename)

      elif comp == 's':
        supertype = 's-comp-aux'
        auxtypename = get_auxtypename(sem, supertype)

        typedef = supertype + ' := aux-lex & basic-one-arg & \
             [ SYNSEM.LOCAL.CAT.VAL [ SUBJ < >, \
                                      COMPS < #comps >, \
                                      SPR < >, \
                                      SPEC < > ], \
               ARG-ST < #comps & \
                        [ LOCAL.CAT [ VAL [ SUBJ < >, \
                                            COMPS < > ], \
                                      HEAD verb ]] > ].'
        mylang.add(typedef)

        if sem == 'add-pred':
          mylang.add_literal('; S comp aux, with pred')

          typedef = auxtypename + ' := ' + supertype + ' & hcons-lex-item & \
                [ SYNSEM [ LOCAL.CONT.HCONS <! qeq & \
                                               [ HARG #harg, \
                                                 LARG #larg ] !>, \
                           LKEYS.KEYREL event-relation & \
                                        [ ARG1 #harg ]], \
                  ARG-ST < [ LOCAL.CONT.HOOK.LTOP #larg ] > ].'
          mylang.add(typedef)

        else:
          mylang.add_literal('; S comp aux, no predicate')

  # LAP 2008-06-11 FIX this: literals may print more than once
  #   here and elsewhere in the loop
          comment = \
            '; Better say [ AUX - ] on complement here, or we\'ll spin' + \
            '; on generation.'
          mylang.add_literal(comment)

          typedef = auxtypename + ' := ' + supertype + ' & raise-sem-lex-item & \
               [ ARG-ST < [ LOCAL.CAT.HEAD.AUX - ] > ].'
          mylang.add(typedef)
          
        customize_users_auxtype(userstypename, auxtypename)
      
      # add stems to lexicon
      ch.iter_begin('stem')
      while ch.iter_valid():
        orth = ch.get('orth')
        typedef = TDLencode(orth) + ' := ' + userstypename + ' & \
                       [ STEM < "' + orth + '" > ].'
        lexicon.add(typedef)

        if sem == 'add-pred':
          pred = ch.get('pred')
          typedef = TDLencode(orth) + \
                    ' := [ SYNSEM.LKEYS.KEYREL.PRED "' + pred + '" ].'
          lexicon.add(typedef, merge=True)

        ch.iter_next()
      ch.iter_end()

      ch.iter_next()
    ch.iter_end()


def customize_determiners():

  # Lexical type for determiners, if the language has any:
  if ch.get('has-dets') == 'yes':
    comment = \
      ';;; Determiners\n' + \
      ';;; SPEC is non-empty, and already specified by basic-determiner-lex.'
    mylang.add_literal(comment)

    typedef = \
      'determiner-lex := basic-determiner-lex & basic-zero-arg & \
          [ SYNSEM.LOCAL.CAT.VAL [ SPR < >, \
                                   COMPS < >, \
                                   SUBJ < > ]].'
    mylang.add(typedef)

  # Determiners
  if ch.get('det1_orth'):
    lexicon.add_literal(';;; Determiners')

  ch.iter_begin('det')
  while ch.iter_valid():
    name = get_name()

    stype = 'determiner-lex'
    dtype = name + '-determiner-lex'

    mylang.add(dtype + ' := ' + stype + '.')

    customize_feature_values(dtype, 'det')

    ch.iter_begin('stem')
    while ch.iter_valid():
      orth = ch.get('orth')
      pred = ch.get('pred')
      typedef = \
        TDLencode(orth) + ' := ' + dtype + ' & \
                    [ STEM < "' + orth + '" >, \
                      SYNSEM.LKEYS.KEYREL.PRED "' + pred + '" ].'
      lexicon.add(typedef)

      ch.iter_next()
    ch.iter_end()

    ch.iter_next()
  ch.iter_end()


def customize_misc_lex():

  #lexicon.add_literal(';;; Other')

  # Question particle
  if ch.get('q-part'):
    orth = ch.get('q-part-orth')
    typedef = \
      TDLencode(orth) + ' := qpart-lex-item & \
                   [ STEM < "' + orth + '" > ].'
    lexicon.add(typedef)


def customize_lexicon():

  customize_nouns()
  customize_case_adpositions()
  customize_verbs()
  customize_auxiliaries()
  customize_determiners()
  customize_misc_lex()


######################################################################
# customize_inflection(matrix_path)
#   Create lexical rules based on the current choices

def is_ltow(name, namelist = []):
  # The simple way to find lexeme-to-word rules is by finding
  # the last non-optional rule. This function recursively searches
  # rules that can follow this one to find non-optional rules.
  # This needs to be fixed: if the rules are circular, this function
  # will recurse infintely.
  if '_' in name:
    name = name.replace('_', '')

  state = ch.iter_state()
  ch.iter_reset()

  for slotprefix in ('noun', 'verb', 'det', 'aux'):
    ch.iter_begin(slotprefix + '-slot')
    while ch.iter_valid():
      n = ch.iter_prefix()
      opt = ch.get('opt')
      ch.iter_begin('input')
      while ch.iter_valid():
        if name in ch.get('type'):
          if name in namelist:
            ch.iter_set_state(state)
            return False
          if opt:
            ch.iter_set_state(state)
            namelist.append(name)
            return is_ltow(n, namelist)
          else:
            ch.iter_set_state(state)
            return False
        ch.iter_next()
      ch.iter_end()
      ch.iter_next()
    ch.iter_end()

  ch.iter_set_state(state)
  return True


def back_to_word(name):
  state = ch.iter_state()
  ch.iter_reset()

  for slotprefix in ('noun', 'verb', 'det', 'aux'):
    ch.iter_begin(slotprefix + '-slot')
    while ch.iter_valid():
      ch.iter_begin('constraint')
      while ch.iter_valid():
        if ch.get('type') == 'forces' and ch.get('other-slot') == name:
          ch.iter_set_state(state)
          return True
        ch.iter_next()
      ch.iter_end()
      ch.iter_next()
    ch.iter_end()

  ch.iter_set_state(state)
  return False


def find_basetype(slot, root_dict, root_list=[]):
  state = ch.iter_state()
  ch.iter_reset()

  ch.iter_begin(slot)
  ch.iter_begin('input')
  while ch.iter_valid():
    inputtype = ch.get('type')
    if inputtype in root_dict and inputtype not in root_list:
      root_list.append(inputtype)
    else:
      root_list = find_basetype(inputtype, root_dict, root_list)
    ch.iter_next()
  ch.iter_end()
  ch.iter_end()

  ch.iter_set_state(state)
  return root_list

def intermediate_rule(slot, root_dict, inp=None, depth=0, opt=False):
  if not inp:
    inp = ch.get_full(slot + '_name') + '-rule-dtr'
    mylang.add(inp + ' := avm.')
 
  if depth and not ch.get_full(slot + '_opt'):
    nonopt = True
    return nonopt, inp

  ch.iter_begin('input')
  while ch.iter_valid():
    i = ch.get('type')
    if i not in root_dict:
      mylang.add(get_name(i) + '-lex-rule := ' + inp + '.')
      if ch.get_full(i + '_opt'):
        state1 = ch.iter_state()
        ch.iter_reset()
        ch.iter_begin(i)
        ch.iter_begin('input')
        while ch.iter_valid():
          rec = ch.get('type')
          if rec not in root_dict:
            mylang.add(get_name(rec) + '-lex-rule := ' + inp + '.')
            state2 = ch.iter_state()
            ch.iter_reset()
            ch.iter_begin(rec)
            opt, inp = intermediate_rule(rec, root_dict, inp, depth+1, opt)
            ch.iter_set_state(state2)
          ch.iter_next()
        ch.iter_set_state(state1)
    ch.iter_next()
  ch.iter_end()

  return opt, inp

def alltypes(type_list, root_list):
  all = True
  for t in type_list:
    if t not in root_list:
      all = False
      break
  return all

def customize_inflection():
  # Build a rule hierarchy for inflectional affixes.

  features = ch.features()
  cases = ch.cases()

  # Create the scale governing direct-inverse marking.
  customize_direct_inverse()

  # root_dict is a dictionary mapping the choices file encodings
  # to the actual rule names.   
  root_dict = {'noun':'noun-lex',
               'verb':'verb-lex',
               'iverb':'intransitive-verb-lex',
               'tverb':'transitive-verb-lex',
               'mverb':'main-verb-lex',
               'det':'determiner-lex',
	       'aux':'aux-lex'}

  # KAO 2008-7-18 Faking the hierarchy for now by assuming that
  # all the verbs/auxiliaries will inherit from 
  verb_types = ['iverb', 'tverb', 'aux']
  main_verb_types = ['iverb', 'tverb',]

# root_dict = {}
  for lexprefix in ('noun', 'verb', 'det', 'aux'):
    ch.iter_begin(lexprefix)
    while ch.iter_valid():
      p = ch.iter_prefix()[:-1]
      n = get_name(p)
      if p in root_dict:
        ch.iter_next()
        continue
      l = lexprefix
      if l == 'det':
        l = 'determiner'

      # If the lexical type is a direct-inverse verb, later rules
      # should use its mandatory rules as input rather than the
      # lexical type.  Create those rules here and put their supertype
      # in the root_dict.
      if lexprefix == 'verb' and ch.get('valence')[-6:] == 'dirinv':
        ltow = is_ltow(ch.iter_prefix()[:-1])
        if ltow:
          super_type = 'const-ltow-rule'
        else:
          super_type = 'const-ltol-rule & add-only-no-ccont-rule'

        direc_geom = ''
        for f in features:
          if f[0] == 'direction':
            direc_geom = f[2]

        rule_type = n + '-dir-inv-lex-rule'
        input_type = n + '-verb-lex'
        mylang.add(
          rule_type + ' := ' + super_type + ' & ' + \
          '[ DTR ' + input_type + ' ].')
        mylang.add(input_type + ' := [ INFLECTED - ].')

        super_type = rule_type

        for direc in ['dir', 'inv']:
          direc_type = n + '-' + direc + '-lex-rule'
          mylang.add(direc_type + ' := ' + super_type + ' &' + \
                     '[ SYNSEM.' + direc_geom + ' ' + direc + ' ].')
          if ch.has_SCARGS():
            if direc == 'dir':
              mylang.add(direc_type + ' := \
                           [ SC-ARGS < #1, #2 >, \
                             SYNSEM.LOCAL.CAT.VAL [ SUBJ < #1 >, \
                                                    COMPS < #2 > ] ].')
            else:
              mylang.add(direc_type + ' := \
                           [ SC-ARGS < #1, #2 >, \
                             SYNSEM.LOCAL.CAT.VAL [ SUBJ < #2 >, \
                                                    COMPS < #1 > ] ].')

          size = direct_inverse_scale_size()
          i = 1
          equal = ch.get_full('scale-equal')

          while i <= size:
            if i == size and not (equal == 'direct' and direc == 'dir'):
              break
            
            rule_type = direc_type + '-' + str(i)

            if equal == 'direct' and direc == 'dir':
              if i == 1:
                hi_type = 'dir-inv-1'
                lo_type = 'dir-inv-scale'
              elif i == size:
                hi_type = lo_type = 'dir-inv-non-' + str(i-1)
              else:
                hi_type = 'dir-inv-' + str(i)
                lo_type = 'dir-inv-non-' + str(i-1)
            else:
              hi_type = 'dir-inv-' + str(i)
              lo_type = 'dir-inv-non-' + str(i)

            if direc == 'dir':
              subj_type = hi_type
              comps_type = lo_type
            else:
              subj_type = lo_type
              comps_type = hi_type

            mylang.add(
              rule_type + ' := ' + direc_type + ' &' + \
              '[ SYNSEM.LOCAL.CAT.VAL [ SUBJ < ' + subj_type + ' >,' + \
              '                         COMPS < ' + comps_type + ' > ] ].')
            lrules.add(
              n + '-' + direc + '-' + str(i+1) + ' := ' + rule_type + '.')

            i += 1

        root_dict[p] = n + '-dir-inv-lex-rule'
      else:
        root_dict[p] = n + '-' + l + '-lex'

      ch.iter_next()
    ch.iter_end()


  # reqs1, reqs2, reqd, and tracker are all used to keep track
  # of non-consecutive dependencies between paradigms.
  reqs1 = {}
  reqs2 = {}
  reqd = []
  tracker = False

  # Big main loop to iterate over all the slots
  for slotprefix in ('noun', 'verb', 'det','aux'):
    ch.iter_begin(slotprefix + '-slot')
    while ch.iter_valid():
      order = ch.get('order')
      opt = ch.get('opt')
      name = get_name()

      if order == 'before':
        aff = 'prefix'
      else:
        aff = 'suffix'
      basetype = []  # list of roots this affix can attach to

      # populate the basetype list with the appropriate values
      root_list = find_basetype(ch.iter_prefix().rstrip('_'), root_dict, [])
      if has_auxiliaries_p():
        if alltypes(verb_types, root_list):
          root_list.append('verb')
        if alltypes(main_verb_types, root_list):
          root_list.append('mverb')
      else:
        if alltypes(main_verb_types, root_list):
          root_list.append('verb')

      for r in root_list:
        if 'verb' in root_list and r in verb_types:
          continue
        elif 'mverb' in root_list and r in main_verb_types:
          continue
        basetype.append(root_dict[r])

      # find the number of input values so we know if it has 1 or more
      inputs = 0
      ch.iter_begin('input')
      while ch.iter_valid():
        inputs += 1
        i_type = ch.get('type')
        ch.iter_next()
      ch.iter_end()


      # Single Input
      if inputs == 1:
        # If the single daughter is a root, set input to the root name
        if i_type in root_dict:
          inp = root_dict[i_type]
          basetype.append(root_dict[i_type])
        else:
          # If the single input is optional, build an intermediate
          # rule for it and its input values, and set inp to the
          # intermediate rule type
          if ch.get_full(i_type+'_opt'):
            non_opt, inp = intermediate_rule(ch.iter_prefix().rstrip('_'),
                                             root_dict)
            # non_opt tracks if there is a non-optional rule that occurs
            # between this rule and the basetype. If not, we need all the
            # basetypes to inherit from the intermediate rule as well.
            if not non_opt:
              for bt in basetype:
                mylang.add(bt+' := '+inp+'.')
          # If the single input is non-optional, make it the input value.
          else:
            inp = get_name(i_type) + '-lex-rule'
      # Multiple inputs
      else:
        # Build an intermediate rule
        non_opt, inp = intermediate_rule(ch.iter_prefix().rstrip('_'),
                                         root_dict)
        # If no intervening non-optional rules, have the basetype(s)
        # inherit from the intermediate rule.
        if not non_opt:
          for bt in basetype:
            mylang.add(bt+' := '+inp+'.')

      # If this rule forces another rule to follow it, then we need
      # to define word-to-lexeme rule for this grammar.
      wtol = False
      ch.iter_begin('constraint')
      while ch.iter_valid():
        if ch.get('type') == 'forces':
          wtol = True
        ch.iter_next()
      ch.iter_end()

      if wtol:
        mylang.add('word-to-lexeme-rule := lex-rule &\
                      [INFLECTED -, DTR.INFLECTED +].')

      ltow = (not opt and is_ltow(ch.iter_prefix().rstrip('_'), [])) # lexeme-to-word rule?
      wtoltow = back_to_word(ch.iter_prefix().rstrip('_')) # satisfy a previous word-to-lexeme rule?
      const = False
      subrules = 0
      morph_orth = ''

      # Iterate over the morphemes and their features to see if any
      # element of the paradigm should be a constant-lex-rule, to
      # count up the number of subrules, and to see if any of the
      # morphemes mark case.
      # SS 2009-06-07 added check to see if a const rule which changes the COMPS of the mother to OPT -
      # is needed.  The code assumes that a given slot will have the same co-occurrence restrictions 
      # for all morphemes. i.e. if one morpheme is not permitted to appear with an overt argument 
      # but is required with a dropped argument, all the other morphemes in this slot will have the 
      # same restrictions.  This is necessary because the const rule that 
      # generated will change the value of the COMPS of the mother OPT - for all items which are not 
      # marked by one of morphemes in this slot.
      # SS 2009-06-07 Now adding capability for when the marker is not permitted with a dropped 
      # argument and is required (or optional )overt argument.  This is done by increasing the subrules 
      # count just like above.  The subrules created are different. 

      opt_head_obj = False
      opt_head_subj = False
      drp_head_obj = False
      drp_head_subj = False
      seen_case = False
      ch.iter_begin('morph')
      while ch.iter_valid():
        subrules += 1
        morph_orth = ch.get('orth')
        if morph_orth == '':
          const = True
        if ch.get_full('obj-mark-drop')== 'obj-mark-drop-opt' and ch.get_full('obj-mark-no-drop') == 'obj-mark-no-drop-req':
          drp_head_obj = True
          const = True
        if ch.get_full('subj-mark-drop')== 'subj-mark-drop-opt' and ch.get_full('subj-mark-no-drop') == 'subj-mark-no-drop-req':
          drp_head_subj = True
          const = True
        ch.iter_begin('feat')
        while ch.iter_valid():
          if ch.get('name') == 'case':
            seen_case = True
          if ch.get('name') == 'overt-arg':
            if ch.get('head') == 'obj':
              opt_head_obj = True
            elif ch.get('head') == 'subj':
              opt_head_subj = True
            const = True
          if ch.get('name') == 'dropped-arg':
            if ch.get('head') == 'obj':
              drp_head_obj = True
            elif ch.get('head') == 'subj':
              drp_head_subj = True
            const = True
          ch.iter_next()
        ch.iter_end()
        
        ch.iter_next()
      ch.iter_end()

      synth_cases = []
      if seen_case and ch.has_mixed_case():
        for c in cases:
          if ch.has_adp_case(c[0]):
            const = True
            synth_cases += [ c[0] ]

      subrules += len(synth_cases)
      
      if (opt_head_obj) or (opt_head_subj):
        subrules += 1
      if (drp_head_obj) or (drp_head_subj):
        subrules += 1

      # Need to specify whether each rule is ltol, ltow, or wtol AND
      # whether the rule is constant or inflecting. Trying to put as much
      # information in the supertype as possible.

      # Specify information for supertype
      if ltow or wtoltow:
        if const:
          if subrules > 0:
            mylang.add(name+'-lex-rule := lexeme-to-word-rule & \
            [DTR ' + inp + '].')
          else:
            mylang.add(name+'-lex-rule := const-ltow-rule & \
            [DTR ' + inp + '].')
        else:
          mylang.add(name+'-lex-rule := infl-ltow-rule & \
          [DTR ' + inp + '].')
        if basetype:
          for bt in basetype:
            mylang.add(bt+ " := [INFLECTED -].")

      elif wtol:
        if const:
          if subrules > 0:
            mylang.add(name+'-lex-rule := word-to-lexeme-rule &\
            [DTR ' + inp + '].')
          else:
            mylang.add(name+'-lex-rule := word-to-lexeme-rule & constant-lex-rule &\
            [DTR ' + inp + '].')
        else:
          mylang.add(name+'-lex-rule := word-to-lexeme-rule & inflecting-lex-rule &\
          [DTR ' + inp + '].')

      else:
        if const:
          if subrules > 0:
            mylang.add(name+'-lex-rule := lexeme-to-lexeme-rule & \
                                          add-only-no-ccont-rule & \
            [DTR ' + inp + '].')
          else:
            mylang.add(name+'-lex-rule := const-add-only-no-ccont-ltol-rule & \
            [DTR ' + inp + '].')
        else:
          if neginflrule(features):
            mylang.add(name+'-lex-rule := infl-cont-change-only-ltol-rule & \
             [DTR ' + inp + '].')
          else:
            mylang.add(name+'-lex-rule := infl-add-only-no-ccont-ltol-rule & \
             [DTR ' + inp + '].')

      # Specify for subtypes, if any
      if subrules > 0:
        morphcount = 0
        ch.iter_begin('morph')
        while ch.iter_valid():
          morphcount += 1
          morphname = ch.get('name')
          if not morphname:
            if name:
              morphname = name + '-morph' + str(morphcount)
            else:
              morphname = get_name()

          # The lexical type and the super-type names
          ltype = morphname + '-lex-rule'
          stype = name + '-lex-rule'

          # Create appropriate sub-rule for the morpheme
          if ch.get('orth') == '':
            if ltow:
              mylang.add(ltype + ' := const-ltow-rule & ' + stype + '.')
            elif wtol:
              mylang.add(ltype + ' := constant-lex-rule & ' + stype + '.')
            else:
              mylang.add(ltype + ' := const-ltol-rule & ' + stype + '.')
            lrules.add(morphname + '-lex := ' + ltype + '.')
          else:
            if const:
              if ltow:
                mylang.add(ltype + ' := infl-ltow-rule & ' + stype + '.')
              elif wtol:
                mylang.add(ltype + ' := inflecting-lex-rule & ' + stype + '.')
              else:
                mylang.add(ltype + ' := infl-ltol-rule & ' + stype + '.')
            elif morphname != name:
              mylang.add(ltype + ' := ' + stype + '.')
            add_irule(morphname + '-' + aff,
                      ltype,
                      aff,
                      ch.get('orth'))

          # Apply the features to the lexical rule
          customize_feature_values(ltype, slotprefix, features, cases)

          ch.iter_next()

          # Before we finish, synthesize any necessary const
          # case-marking rules
          if not ch.iter_valid() and synth_cases:
            geom = ''
            for f in features:
              if f[0] == 'case':
                geom = f[2]

            # create a rule for each case that needs it
            for c in synth_cases:
              morphname = name + '-synth-' + c
              ltype = morphname + '-lex-rule'
              if ltow:
                mylang.add(ltype + ' := const-ltow-rule & ' + stype + '.')
              elif wtol:
                mylang.add(ltype + ' := constant-lex-rule & ' + stype + '.')
              else:
                mylang.add(ltype + ' := const-ltol-rule & ' + stype + '.')
              lrules.add(morphname + '-lex := ' + ltype + '.')

              abbr = canon_to_abbr(c, cases)
              mylang.add(ltype + ' := [ SYNSEM.' + geom + ' ' + abbr + ' ].')
  
          if not ch.iter_valid() and (opt_head_obj or opt_head_subj):
            ltype = name + '-no-drop-lex-rule'
            if ltow:
              mylang.add(ltype + ' := const-ltow-rule & ' + stype + '.')
            elif wtol:
              mylang.add(ltype + ' := constant-lex-rule & ' + stype + '.')
            else:
              mylang.add(ltype + ' := const-ltol-rule & ' + stype + '.')
            lrules.add(name + '-no-drop-lex := ' + name + '-no-drop-lex-rule.')
            if (opt_head_obj):
             mylang.add(ltype + ':= [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)
            if (opt_head_subj):
              mylang.add(ltype + ':= [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT -].', merge = True)

          if not ch.iter_valid() and (drp_head_obj or drp_head_subj):
            ltype = name + '-drop-lex-rule'
            if ltow:
              mylang.add(ltype + ' := const-ltow-rule & ' + stype + '.')
            elif wtol:
              mylang.add(ltype + ' := constant-lex-rule & ' + stype + '.')
            else:
              mylang.add(ltype + ' := const-ltol-rule & ' + stype + '.')
            lrules.add(name + '-drop-lex := ' + name + '-drop-lex-rule.')
            if (drp_head_obj):
             mylang.add(ltype + ':= [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT +].', merge = True)
            if (drp_head_subj):
              mylang.add(ltype + ':= [SYNSEM.LOCAL.CAT.VAL.COMPS.FIRST.OPT +].', merge = True)
            
        ch.iter_end()
      else:
        if const:
          lrules.add(name + '-lex := ' + name + '-lex-rule.')
        else:
          add_irule(name + '-' + aff,
                    name + '-lex-rule',
                    aff,
                    morph_orth)

      # Keep track of non-consecutive requirements
      reqs1, reqd = req(basetype, reqs1, reqd, tracker, 'req')
      reqs2, reqd = req(basetype, reqs2, reqd, tracker, 'disreq')

      # Done with this slot, go on to the next one
      ch.iter_next()

    # Done with slots
    ch.iter_end()

  # For rules that have requirements, we need to copy up all the other
  # TRACK information
  add_single_tracks(reqs1, reqd, 'req')
  add_single_tracks(reqs2, reqd, 'disreq')

  # For all other rules, copy up the whole TRACK feature
  if reqd:
    copy_all_tracks(reqd)


def req(basetype, reqs, reqd, tracker, reqtype):
  stype = ch.iter_prefix().rstrip('_') # slot type; assumes req() has been called from a 'slot' context.
  name = "T-"+get_name(stype)

  seen_reqtype = False
  ch.iter_begin('constraint')
  while ch.iter_valid():
    if ch.get('type') == reqtype:
      if not seen_reqtype:
        seen_reqtype = True

        # Keep track of rules having non-consecutive co-occurence constraints
        reqs[stype] = []
        reqd.append(stype)

        # If this is the first rule that has a TRACK requirement, we need
        # to add the feature TRACK
        if not tracker:
          mylang.add('track := avm.')
          mylang.add('word-or-lexrule :+ [TRACK track].')
          tracker = True

      # Keep track of which rules have been constrained
      other = ch.get('other-slot')
      reqd.append(other)
      reqs[stype].append(other)

      # Add a feature to track corresponding to this rule.
      mylang.add('track :+ [' + name + ' bool].')

      # Set the root type(s) as having the track feature corresponding
      # to this rule as + or -
      if reqtype == 'req':
        val = '-'
      elif reqtype == 'disreq':
        val = '+'

      for bt in basetype:
        mylang.add(bt + ':= [TRACK.' + name + ' ' + val + ' ].')

    ch.iter_next()
  ch.iter_end()

  return reqs, reqd

def add_single_tracks(reqs, reqd, reqtype):
  # Begin iterating over slots
  for slotprefix in ('noun', 'verb', 'det', 'aux'):
    ch.iter_begin(slotprefix + '-slot')
    while ch.iter_valid():
      slot = ch.iter_prefix().rstrip('_')
      name = get_name(slot)
      tname = "T-"+name
      # We only need to do this for rules with TRACK constraints.
      if slot not in reqs:
        ch.iter_next()
        continue
      # Start a second slot loop
      state = ch.iter_state()
      ch.iter_reset()
      for slotprefix2 in ('noun', 'verb', 'det', 'aux'):
        ch.iter_begin(slotprefix2 + '-slot')
        while ch.iter_valid():
          s2 = ch.iter_prefix().rstrip('_')
          # Skip this slot if it's the same as the one in the outer loop.
          if s2 == slot:
            ch.iter_next()
            continue
          name2 = get_name(s2)
          # If the inner-loop rule sets or fulfills a constraint on the
          # outer-loop rule constrain the TRACK values of each rule as
          # appropriate.
          if s2 in reqs[slot]:
            if reqtype == 'req':
              mylang.add(name+'-lex-rule := [TRACK.'+tname+' -, DTR.TRACK.'+tname+' +].')
              mylang.add(name2+'-lex-rule := [TRACK.'+tname+' +, DTR.TRACK.'+tname+' -].')
            elif reqtype == 'disreq':
              mylang.add(name+'-lex-rule := [TRACK.'+tname+' -, DTR.TRACK.'+tname+' +].')
              mylang.add(name2+'-lex-rule := [TRACK.'+tname+' -, DTR.TRACK.'+tname+' +].')
          # If this rule doesn't have anything to say about the outer-loop
          # rule, but has TRACK constraints for other rules, we need to
          # copy up the TRACK feature corresponding to the outer-loop
          # rule.
          elif s2 in reqs or s2 in reqd:
            mylang.add(name2+'-lex-rule := [TRACK.'+tname+' #track, DTR.TRACK.'+tname+' #track].')
          ch.iter_next()
        ch.iter_end()
      ch.iter_set_state(state)
      ch.iter_next()
    ch.iter_end()

def copy_all_tracks(reqd):
  # If a grammar makes use of the TRACK feature, inflectional rules
  # that don't have anything to say about the contents of TRACK need
  # to copy the whole TRACK feature up unchanged.
  for slotprefix in ('noun', 'verb', 'det', 'aux'):
    ch.iter_begin(slotprefix + '-slot')
    while ch.iter_valid():
      slot = ch.iter_prefix().rstrip('_')
      name = get_name(slot)
      if slot not in reqd:
        mylang.add(name + '-lex-rule := [TRACK #track, \
        DTR.TRACK #track].')
      ch.iter_next()
    ch.iter_end()


def neginflrule(features):
  # ERB 2009-01-23
  # Subroutine for determining if the rule at hand is the type
  # that needs to add negative semantics (negative inflection lex rule)
  # FIXME: For now assuming that negation will always be in a slot
  # by itself, so that if one morpheme in a slot needs to be a 
  # cont-change-only-lex-rule, they all do.  This is wrong, but fixing
  # it properly requires refactoring the morphotactic code, I'm afraid.
  # Where this is currently being called, it seems to be inside another
  # iter_begin(), and so the prefix is already set appropriately.
  # Check whether this is so when using this function in new contexts.
  result = False
  ch.iter_begin('morph')
  while ch.iter_valid():
    ch.iter_begin('feat')
    while ch.iter_valid():
      name = ch.get('name')
      value = ch.get('value')
      if (name == 'negation' and value == 'plus'):
        result = True
      ch.iter_next()
    ch.iter_end()
    ch.iter_next()
  ch.iter_end()
        
  return result

######################################################################
# customize_test_sentences(matrix_path)
#   Create the script file entries for the user's test sentences.

def customize_test_sentences(matrix_path):
  try:
    b = open('matrix-core/basic_script', 'r')
    s = open(matrix_path + 'lkb/script', 'w')
    lines = b.readlines()
    b.close()
    for l in lines:
      l = l.strip()
      if l == ';;; Modules: LOAD my_language.tdl':
        myl = ch.get('language').lower() + '.tdl'
        s.write('   (lkb-pathname (parent-directory) "' + myl + '")\n')
      elif l == ';;; Modules: Default sentences':
        s1 = ch.get('sentence1')
        s2 = ch.get('sentence2')
        s.write('(if (eq (length *last-parses*) 1)\n')
        s.write('   (setf *last-parses* \'("' + s1 + '" "' + s2 + '")))\n')
      else:
        s.write(l + '\n')
    s.close()
  except:
    pass


######################################################################
# customize_roots()
#   Create the file roots.tdl

def customize_roots():
  comment = \
    'A sample start symbol: Accept fully-saturated verbal\n' + \
    'projections only; if a grammar makes use of the head-subject and\n' + \
    'head-complement types as provided by the Matrix, this should be a\n' + \
    'good starting point.  Note that it is legal to have multiple start\n' + \
    'symbols, but they all need to be listed as the value of\n' + \
    '`*start-symbol\' (see `lkb/user-fns.lsp\').'
# ERB 2006-10-05 Removing if statement from within string

#  verb_addendum = ''
#  if has_auxiliaries_p():
#    verb_addendum = ' & [ FORM fin ]'
#[ HEAD verb' + verb_addendum + ', \

  # ERB 2007-01-21 Need to add [MC +] for inversion strategy for
  # questions, but it's hard to see how this could hurt in general,
  # so let's just put it in.

  typedef = \
    'root := phrase & \
       [ SYNSEM.LOCAL [ CAT [ VAL [ SUBJ < >, \
                                    COMPS < > ], \
                              MC + ],\
                        COORD - ] ].'
  roots.add(typedef, comment)

  if has_auxiliaries_p() or ch.is_set_full('noaux-fin-nf'):
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD.FORM finite ].')

  # ERB 2006-10-05 I predict a bug here:  If we a language with auxiliaries
  # and question particles, we're going to need to make sure that FORM is
  # compatible with comp.

  if ch.get('q-part'):
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD +vc ].')
  else:
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD verb ].')

  comment = \
    'This start symbol allows you to parse single words as stand-alone\n' + \
    'utterances.  This can be useful for grammar debugging purposes.'
  typedef = \
    'lex-root := word-or-lexrule.'
  roots.add(typedef, comment)


######################################################################
# Archive helper functions
#   make_tgz(dir) and make_zip(dir) create an archive called
#   dir.(tar.gz|zip) that contains the contents of dir

def make_tgz(dir):

  # ERB First get rid of existing file because gzip won't
  # overwrite existing .tgz meaning you can only customize
  # grammar once per session.

  if os.path.exists('matrix.tar.gz'):
    os.remove('matrix.tar.gz')

  archive = dir + '.tar'
  t = tarfile.open(archive, 'w')
  t.add(dir)
  t.close()

  if os.name == 'nt':
    g = gzip.open(archive + '.gz', 'wb')
    f = open(archive, 'rb')
    g.write(f.read())
    f.close()
    g.close()
  else:
    os.system('gzip ' + archive)


def add_zip_files(z, dir):
  files = os.listdir(dir)
  for f in files:
    cur = dir + '/' + f
    if os.path.isdir(cur):
      add_zip_files(z, cur)
    else:
      z.write(cur, cur)


def make_zip(dir):
  z = zipfile.ZipFile(dir + '.zip', 'w')
  add_zip_files(z, dir)
  z.close()


######################################################################
# customize_matrix(path)
#   Create and prepare for download a copy of the matrix based on
#   the choices file in the directory 'path'.  This function
#   assumes that validation of the choices has already occurred.

def customize_matrix(path, arch_type):
  choices_file = path + '/choices'
  global ch
  ch = ChoicesFile(choices_file)

  matrix_path = path + '/matrix/'

  # Copy from matrix-core
  if os.path.exists(matrix_path):
    shutil.rmtree(matrix_path)
  shutil.copytree('matrix-core', matrix_path)
  shutil.copy(choices_file, matrix_path) # include a copy of choices

  # Create TDL object for each output file
  global mylang, rules, irules, lrules, lexicon, roots
  mylang =  tdl.TDLfile(matrix_path + ch.get('language').lower() + '.tdl')
  rules =   tdl.TDLfile(matrix_path + 'rules.tdl')
  irules =  tdl.TDLfile(matrix_path + 'irules.tdl')
  lrules =  tdl.TDLfile(matrix_path + 'lrules.tdl')
  lexicon = tdl.TDLfile(matrix_path + 'lexicon.tdl', False)
  roots =   tdl.TDLfile(matrix_path + 'roots.tdl')

  # date/time
  try:
    f = open('datestamp', 'r')
    matrix_dt = f.readlines()[0].strip()
    f.close()
  except:
    matrix_dt= 'unknown time'

  current_dt = datetime.datetime.utcnow()
  tdl_dt = current_dt.strftime('%a %b %d %H:%M:%S UTC %Y')
  lisp_dt = current_dt.strftime('%Y-%m-%d_%H:%M:%S_UTC')

  # Put the current date/time in my_language.tdl...
  mylang.add_literal(';;; Grammar of ' + ch.get('language') + '\n' +
                     ';;; created at:\n' +
                     ';;;     ' + tdl_dt + '\n' +
                     ';;; based on Matrix customization system version of:\n' +
                     ';;;     ' + matrix_dt)

  # BUT, put the date/time of the Matrix version in Version.lsp (along
  # with the name of the language.
  global version_lsp
  version_lsp = tdl.TDLfile(matrix_path + 'Version.lsp')

  version_lsp.add_literal('(in-package :common-lisp-user)\n\n' +
                          '(defparameter *grammar-version* \"' +
                          ch.get('language') + ' (' + lisp_dt + ')\")')

  # Initialize various type hierarchies
  init_case_hierarchy()
  init_person_hierarchy()
  init_number_hierarchy()
  init_pernum_hierarchy()
  init_gender_hierarchy()
  init_tense_hierarchy()
  init_aspect_hierarchy()
  init_situation_hierarchy()
  init_form_hierarchy()
  init_other_hierarchies()

  # Customize inflection and lexicon first, since they can cause
  # augmentation of the hierarchies
  customize_inflection()
  customize_lexicon()

  # Call the other customization functions
  customize_case()
  customize_person_and_number()
  customize_gender()
  customize_form()
  customize_tense()
  customize_aspect()
  customize_situation()
  customize_other_features()
  customize_word_order()
  customize_sentential_negation()
  customize_coordination()
  customize_yesno_questions()
  customize_arg_op()
  customize_test_sentences(matrix_path)
  customize_roots()

  # Save the output files
  mylang.save()
  rules.save()
  irules.save()
  lrules.save()
  lexicon.save()
  roots.save()
  version_lsp.save()

  # Either tar or zip up the results
  old_dir = os.getcwd()
  os.chdir(path)
  if arch_type == 'tgz':
    make_tgz('matrix')
  else:
    make_zip('matrix')
  os.chdir(old_dir)

###############################################################
# Allow customize_matrix() to be called directly from the
# command line or shell scripts.

if __name__ == "__main__":
  customize_matrix(sys.argv[1], 'tgz')
