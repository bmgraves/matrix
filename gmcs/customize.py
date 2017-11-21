#
# $Id: customize.py,v 1.71 2008-09-30 23:50:02 lpoulson Exp $

######################################################################
# imports

import os
import datetime
import shutil
import tdl
import tarfile
import gzip
import zipfile
import sys
import re
import codecs
import extract_feature_geometry
import abbreviate_paths_in_climb
from subprocess import call

from gmcs.choices import ChoicesFile
from gmcs.utils import TDLencode
from gmcs.utils import get_name
from gmcs.utils import format_comment_block

from gmcs.lib import TDLHierarchy

from gmcs.linglib import morphotactics
from gmcs.linglib import argument_optionality
from gmcs.linglib import direct_inverse
from gmcs.linglib import case
from gmcs.linglib import word_order
from gmcs.linglib import word_order_v2_vcluster
from gmcs.linglib import features
from gmcs.linglib import lexical_items
from gmcs.linglib import agreement_features
from gmcs.linglib import verbal_features
from gmcs.linglib import negation
from gmcs.linglib import coordination
from gmcs.linglib import yes_no_questions
from gmcs.linglib import passivization
from gmcs.linglib import toolboximport
from gmcs.linglib import long_distance_dependencies
from gmcs.linglib import extraposition
from gmcs.linglib import comparatives
from gmcs.linglib import argument_alternation

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
trigger = None

# ERB 2006-09-16 There are properties which are derived from the
# choices file as a whole which various modules will want to know about.
# The first example I have is the presence of auxiliaries.  Both the
# negation and yes-no questions modules have cases where they need to
# restrict lexical rules to applying to main verbs only, but only if
# there is in fact a distinction between main and auxiliary verbs (i.e.,
# they need to say [ AUX - ], but only if the feature AUX is defined).

# ERB 2006-10-15 I want this function to return true if an auxiliary is
# defined, even if it's not needed for negation or questions.



####def irule_name(type_name):
####  return re.sub('\s+', '_', type_name)

# ERB 2006-09-21 This function assembles an inflectional rule out
# of the appropriate information and adds it to irules.tdl.
# Assumes we consistently use either 'prefix' and 'suffix' or 'before'
# and 'after' as values in the html form.
# Should this actually be a method on TDLfile?
### ASF 2011-04-04 removed, since no longer used

####def add_irule(instance_name,type_name,affix_type,affix_form):

#  rule = irule_name(instance_name) + ' :=\n'
#  if affix_type == 'prefix' or affix_type == 'before':
#    rule += '%prefix (* ' + affix_form + ')\n'
#  elif affix_type == 'suffix' or affix_type == 'after':
#    rule += '%suffix (* ' + affix_form + ')\n'

# TODO: generate error here.
#  else:
#    error 'probable script bug'


######################################################################
# customize_punctuation(grammar_path)
#   Determine which punctuation characters to ignore in parsing

def customize_punctuation(grammar_path):
  '''sets up repp preprocessing for lkb according to one of 
     three choices on the questionnaire.  '''
    # TODO: pet.set output needs to be updated for 
    # current questionnaire choices and for repp!

  default_splits_str = ' \\t!"#$%&\'()\*\+,-\./:;<=>?@\[\]\^_`{|}~\\\\'.encode('utf-8')

  if ch.get('punctuation-chars') == 'keep-all':
    # in this case, we just split on [ \t], and that's
    # what vanilla.rpp already does, so we're done
    return
  elif ch.get('punctuation-chars') == 'discard-all':
    # in this case, "all" punctuation (from the default list)
    # should be split on and dropped 
    # to do this we have to build a regex for the : line of 
    # the repp file
    # 
    filename = os.path.join(grammar_path, 'lkb', 'vanilla.rpp') 
    lines = codecs.open(filename, 'r', encoding='utf-8').readlines()
    van_rpp = codecs.open(filename, 'w', encoding='utf-8')
    for line in lines:
      if line.startswith(':'):
        line = ":["+default_splits_str+"]".rstrip()
      print >>van_rpp, line.rstrip('\n')
    van_rpp.close()       
  elif ch.get('punctuation-chars') == 'keep-list':
    # here we split on the default list (like discard-all),
    # but *minus* whatevers on the keep list
    chars = list(unicode(ch['punctuation-chars-list'], 'utf8'))
    filename = os.path.join(grammar_path, 'lkb', 'vanilla.rpp') 
    lines = iter(codecs.open(filename, 'r', encoding='utf-8').readlines())
    van_rpp = codecs.open(filename, 'w', encoding='utf-8')
    for line in lines:
      if line.startswith(':'):
        line = line[2:-2]
      # NOTE: repp syntax says that the line that starts with ':'
      # defines a list of chars to split on
        for c in chars:
          # \ char needs some special treatment
          # so do the other escaped chars!
          if c == '\\':
            c = '\\\\'
          default_splits_str = default_splits_str.replace(c,'')
        line= ":["+default_splits_str+"]".rstrip()
      print >>van_rpp,line.rstrip('\n')
    van_rpp.close()

  
#  Need to move pet over to repp
# 
#  # PET's pet.set is a bit easier
#  line_re = re.compile(r'^punctuation-characters := "(.*)".\s*$')
#  # need to escape 1 possibility for PET
#  chars = [{'"':'\\"'}.get(c, c) for c in chars]
#  punc_re = re.compile(r'(' + r'|'.join(re.escape(c) for c in chars) + r')')
#  filename = os.path.join(grammar_path, 'pet', 'pet.set')
#  lines = iter(open(filename, 'r').readlines())
#  pet_set = open(filename, 'w')
#  for line in lines:
#    line = unicode(line, 'utf8')
#    s = line_re.search(line)
#    if s:
#      line = 'punctuation-characters := "%s".' % punc_re.sub('', s.group(1))
#    print >>pet_set, line.rstrip().encode('utf8')
#  pet_set.close()

#####################################################################
#
# adds fragment root as option to globals, if called by choices

def customize_globals(grammar_path):
  
  
  try:
    o_gl = open(os.path.join(grammar_path, 'lkb/globals.lsp'), 'r')
    lines = o_gl.readlines()
    o_gl.close()
    n_gl = open(os.path.join(grammar_path, 'lkb/globals.lsp'), 'w')
    for line in lines:
      if '*start-symbol*' in line:
        n_gl.write('(defparameter *start-symbol* \'(root phrase-root)\n')
      else:
        n_gl.write(line)
    n_gl.close()
  except:
    pass

def customize_root_in_pet(grammar_path):
  try:
    pet_set = open(os.path.join(grammar_path, 'pet/pet.set'), 'r')
    lines = pet_set.readlines()
    pet_set.close()
    new_pet_set = open(os.path.join(grammar_path, 'pet/pet.set'), 'w')
    for line in lines:
      if 'start-symbols := ' in line:
        new_pet_set.write('start-symbols := $root $phrase-root.')
      else:
        new_pet_set.write(line)
    new_pet_set.close()
  except:
    pass

######################################################################
# customize_test_sentences(grammar_path)
#   Create the script file entries for the user's test sentences.

def customize_test_sentences(grammar_path):
  try:
    b = open(os.path.join(grammar_path, 'lkb/script'), 'r')
    lines = b.readlines()
    b.close()
    s = open(os.path.join(grammar_path, 'lkb/script'), 'w')
    ts = open(os.path.join(grammar_path, 'test_sentences'), 'w')
    for l in lines:
      l = l.strip()
      if l == ';;; Modules: Default sentences':
        s.write('(if (eq (length *last-parses*) 1)\n')
        s.write('   (setf *last-parses* \'(')
        if 'sentence' not in ch:
          s.write('""')
        for sentence in ch.get('sentence',[]):
          s.write('"' + sentence.get('orth','') + '" ')
          ts.write(sentence.get('orth','') + '\n')
        s.write(')))\n')
      else:
        s.write(l + '\n')
    s.close()
    ts.close()
  except:
    pass

def customize_itsdb(grammar_path):
  from gmcs.lib import itsdb
  if 'sentence' not in ch: return

  def get_item(s, i):
    return dict([('i-id', str(i+1)),
                 ('i-origin', 'unknown'),
                 ('i-register', 'unknown'),
                 ('i-format', 'none'),
                 ('i-difficulty', '1'),
                 ('i-category', 'S' if not s.get('star', False) else ''),
                 ('i-input', s['orth']),
                 ('i-wf', '0' if s.get('star', False) else '1'),
                 ('i-length', str(len(s['orth'].split()))),
                 ('i-author', 'author-name'),
                 ('i-date', str(datetime.date.today()))])

  skeletons = os.path.join(grammar_path, 'tsdb', 'skeletons')
  relations = os.path.join(skeletons, 'Relations')
  matrix_skeleton = os.path.join(skeletons, 'matrix')
  items = {'item': (get_item(s, i) for i, s in enumerate(ch['sentence']))}
  profile = itsdb.TsdbProfile(matrix_skeleton)
  profile.write_profile(matrix_skeleton, relations, items)

def customize_script(grammar_path):
  try:
    b = open(os.path.join(grammar_path, 'lkb/script'), 'r')
    lines = b.readlines()
    b.close()
    s = open(os.path.join(grammar_path, 'lkb/script'), 'w')
    for l in lines:
      l = l.strip()
      if l == ';;; Modules: LOAD my_language.tdl':
        myl = ch.get('language').lower() + '.tdl'
        s.write('   (lkb-pathname (parent-directory) "' + myl + '")\n')
      else:
        s.write(l + '\n')
    s.close()
  except:
    pass

######################################################################
# customize_pettdl()
#

def customize_pettdl(grammar_path):
  try:
    p_in = open(os.path.join(get_matrix_core_path(), 'pet.tdl'), 'r')
    lines = p_in.readlines()
    p_in.close()
    myl = ch.get('language').lower()
    p_out = open(os.path.join(grammar_path, myl + '-pet.tdl'), 'w')
    for l in lines:
      l = l.strip()
      p_out.write(l + '\n')
      if l == ':include "matrix".':
        p_out.write(':include "' + myl + '".\n')
    p_out.close()
    set_out = open(os.path.join(grammar_path, 'pet/' + myl + '-pet.set'), 'w')
    set_out.write(';;;; settings for CHEAP -*- Mode: TDL; Coding: utf-8 -*-\n')
    set_out.write('include "flop".\n')
    set_out.write('include "pet".\n')
    set_out.close()
  except:
    pass

######################################################################
# customize_acetdl()
#

def customize_acetdl(grammar_path):
  myl = ch.get('language').lower()
  ace_config = os.path.join(grammar_path, 'ace', 'config.tdl')
  replace_strings = {'mylanguage': os.path.join('..', myl + '-pet.tdl')}
  lines = open(ace_config, 'r').read()
  a_out = open(ace_config, 'w')
  print >>a_out, lines % replace_strings
  a_out.close()

######################################################################
# customize_roots()
#   Create the file roots.tdl

def customize_roots(grammar_path):
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
       [ SYNSEM.LOCAL.CAT [ VAL [ SUBJ < >, \
                                    COMPS < > ], \
                              MC + ] ].'
  roots.add(typedef, comment)
  if not ch.get('coord-root') == 'on':
    roots.add('root := [ SYNSEM.LOCAL.COORD - ].')

  if ch.get('has-aux') == 'yes' or 'noaux-fin-nf' in ch:
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD.FORM finite ].')
    # Germanic specific condition
    if ch.get('verb-cluster') == 'yes' and ch.get('split-cluster') == 'yes':
      if ch.get('vc-analysis') == 'aux-rule' or ch.get('split-analysis') == 'lex-rule':
 # adapted setting for new word-order (from left to right)
        roots.add('root := [ SYNSEM.LOCAL.CAT.VFRONT na-or-- ].')
  if ch.get('v2-analysis') == 'filler-gap' or ch.get('ldd'):
    roots.add('root := [ SYNSEM.NON-LOCAL.SLASH <! !> ].') 

  if ch.get('extraposition') == 'yes':
    roots.add('root := [ SYNSEM.LOCAL.ANCHOR.TO-BIND < > ].')
    if ch.get('phrase-root') == 'on':
      roots.add('phrase-root := [ SYNSEM.LOCAL.ANCHOR.TO-BIND < > ].')
  # ERB 2006-10-05 I predict a bug here:  If we a language with auxiliaries
  # and question particles, we're going to need to make sure that FORM is
  # compatible with comp.

  if ch.get('q-part'):
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD +vc ].')
  else:
    roots.add('root := [ SYNSEM.LOCAL.CAT.HEAD verb ].')


  if ch.get('phrase-root') == 'on':
    comment = \
     'This root is for phrases only. Should be turned on when data\n' + \
     'also contains titles of articles or for parsing fragments'
    typedef = \
     '''phrase-root := phrase &
        [ SYNSEM [ NON-LOCAL.SLASH <! !>,
                   LOCAL [ CAT.VAL [ SUBJ < >,
                                     COMPS < > ] ] ] ].'''
    roots.add(typedef, comment) 
    customize_globals(grammar_path)
    customize_root_in_pet(grammar_path)

  comment = \
    'This start symbol allows you to parse single words as stand-alone\n' + \
    'utterances.  This can be useful for grammar debugging purposes.'
  typedef = \
    'lex-root := word-or-lexrule.'
  roots.add(typedef, comment)

  ##1. Add alternative roots (can parse NP or CP)
  ##2. Make sure they are listed in globals





######################################################################
# Version Control
#   Use shell commands to setup Mercurial or Bazaar, if the user
#   has specified that they want one or the other.

def setup_vcs(ch, grammar_path):
  if 'vcs' in ch:
    IGNORE = open(os.devnull,'w')
    cwd = os.getcwd()
    os.chdir(grammar_path)
    if ch['vcs'] == 'git':
      call(['git', 'init'], stdout=IGNORE, stderr=IGNORE)
      call(['git', 'add', '.'], stdout=IGNORE, stderr=IGNORE)
      call(['git', 'commit',
            '--author="Grammar Matrix <matrix-dev@u.washington.edu>"',
            '-m "Initial commit."'], stdout=IGNORE, stderr=IGNORE)
    elif ch['vcs'] == 'hg':
      call(['hg', 'init'], stdout=IGNORE, stderr=IGNORE)
      call(['hg', 'add'], stdout=IGNORE, stderr=IGNORE)
      call(['hg', 'commit',
            '-u Grammar Matrix <matrix-dev@u.washington.edu>',
            '-m "Initial commit."'], stdout=IGNORE, stderr=IGNORE)
    elif ch['vcs'] == 'bzr':
      call(['bzr', 'init'], stdout=IGNORE, stderr=IGNORE)
      call(['bzr', 'add'], stdout=IGNORE, stderr=IGNORE)
      call(['bzr', 'whoami', '--branch',
            'Grammar Matrix Customization System <matrix-dev@uw.edu>'],
           stdout=IGNORE, stderr=IGNORE)
      call(['bzr', 'commit', '-m "Initial commit."'],
           stdout=IGNORE, stderr=IGNORE)
    os.chdir(cwd)
    IGNORE.close()


def create_climb_files_dict(grammar_path):

  climb_dict = {}
  climb_dict['lexical_items'] =  tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'lexical_items.tdl'))
  climb_dict['nouns'] =  tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'nouns.tdl'))
  climb_dict['verbs'] =  tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'verbs.tdl'))
  climb_dict['case'] =  tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'case.tdl'))
  climb_dict['aux'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'auxiliaries.tdl'))
  climb_dict['cop'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'copula.tdl'))
  climb_dict['wh'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'wh-analyses.tdl'))
  climb_dict['arg-opt'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'argument_optionality.tdl'))
  climb_dict['arg-alternation'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'argument_alternation.tdl'))
  climb_dict['morph'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'morphotactics.tdl'))
  climb_dict['agreement'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'agreement.tdl'))
  climb_dict['verbal-feat'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'verbal_features.tdl'))
  climb_dict['word-order'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'word_order.tdl'))
  climb_dict['ger-wo'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'germanic_word_order.tdl'))
  climb_dict['neg'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'negation.tdl'))
  climb_dict['coord'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'coordination.tdl'))
  climb_dict['polar-q'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'polar_questions.tdl'))
  climb_dict['pass'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'passivization.tdl'))
  climb_dict['ldd'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'long_distance_dep.tdl'))
  climb_dict['extrapos'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'extraposition.tdl'))
  climb_dict['compar'] = tdl.TDLfile(os.path.join(grammar_path + '/climb/', 'comparatives.tdl'))

  climb_dict['lexical_items'].define_climb_sections()
  climb_dict['nouns'].define_climb_sections()
  climb_dict['verbs'].define_climb_sections()
  climb_dict['case'].define_climb_sections()
  climb_dict['aux'].define_climb_sections()
  climb_dict['cop'].define_climb_sections()
  climb_dict['wh'].define_climb_sections()
  climb_dict['arg-opt'].define_climb_sections()
  climb_dict['arg-alternation'].define_climb_sections()
  climb_dict['morph'].define_climb_sections()
  climb_dict['agreement'].define_climb_sections()
  climb_dict['verbal-feat'].define_climb_sections()
  climb_dict['word-order'].define_climb_sections()
  climb_dict['ger-wo'].define_climb_sections()
  climb_dict['neg'].define_climb_sections()
  climb_dict['coord'].define_climb_sections()
  climb_dict['polar-q'].define_climb_sections()
  climb_dict['pass'].define_climb_sections()
  climb_dict['ldd'].define_climb_sections()
  climb_dict['extrapos'].define_climb_sections()
  climb_dict['compar'].define_climb_sections()

  return climb_dict


######################################################################
# customize_matrix(path)
#   Create and prepare for download a copy of the matrix based on
#   the choices file in the directory 'path'.  This function
#   assumes that validation of the choices has already occurred.

def customize_matrix(path, arch_type, destination=None):
  if os.path.isdir(path):
    path = os.path.join(path, 'choices')
  # if no destination dir is specified, just use the choices file's dir
  destination = destination or os.path.dirname(path)

  global ch
  ch = ChoicesFile(path)

  language = ch['language']

  grammar_path = get_grammar_path(ch.get('iso-code', language).lower(),
                                  language.lower(), destination)

  # delete any existing contents at grammar path
  if os.path.exists(grammar_path):
    shutil.rmtree(grammar_path)
  # the rsync command won't create the target dirs, so do it now
  os.makedirs(grammar_path)
  # creating a climb directory
  
  os.makedirs(grammar_path + '/climb')



  # Use the following command when python2.6 is available
  #shutil.copytree('matrix-core', grammar_path,
  #                ignore=shutil.ignore_patterns('.svn'))
  IGNORE = open(os.devnull, 'w')
  call(['rsync', '-a', '--exclude=.svn',
        get_matrix_core_path() + os.path.sep, grammar_path],
       stdout=IGNORE, stderr=IGNORE)
  IGNORE.close()
  
  # include copy of CLIMB material
  
  IGNORE = open(os.devnull, 'w')
  call(['rsync', '-a', '--exclude=.svn',
        get_climb_path() + os.path.sep, grammar_path + '/climb'],
       stdout=IGNORE, stderr=IGNORE)
  IGNORE.close()
  

  # include a copy of choices (named 'choices' to avoid collisions)
  shutil.copy(path, os.path.join(grammar_path, 'choices'))

  # Create TDL object for each output file
  global mylang, rules, irules, lrules, lexicon, roots
  mylang =  tdl.TDLfile(os.path.join(grammar_path, language.lower() + '.tdl'))
  mylang.define_sections([['addenda', 'Matrix Type Addenda', True, False],
                          ['features', 'Features', True, False],
                          ['dirinv', 'Direct-Inverse', True, False],
                          ['lextypes', 'Lexical Types', True, True],
                          ['nounlex', 'Nouns', False, False],
                          ['verblex', 'Verbs', False, False],
                          ['auxlex', 'Auxiliaries', False, False],
                          ['otherlex', 'Others', False, False],
                          ['lexrules', 'Lexical Rules', True, False],
                          ['phrases', 'Phrasal Types', True, False],
                          ['coord', 'Coordination', True, False]])
  rules =   tdl.TDLfile(os.path.join(grammar_path, 'rules.tdl'))
  irules =  tdl.TDLfile(os.path.join(grammar_path, 'irules.tdl'))
  lrules =  tdl.TDLfile(os.path.join(grammar_path, 'lrules.tdl'))
  lexicon = tdl.TDLfile(os.path.join(grammar_path, 'lexicon.tdl'))
  roots =   tdl.TDLfile(os.path.join(grammar_path, 'roots.tdl'))
  trigger = tdl.TDLfile(os.path.join(grammar_path, 'trigger.mtr'))
  trigger.add_literal(';;; Semantically Empty Lexical Entries')

  climb_files = create_climb_files_dict(grammar_path)


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
  mylang.add_literal(
    ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;\n' +
    ';;; Grammar of ' + ch.get('language') + '\n' +
    ';;; created at:\n' +
    ';;;     ' + tdl_dt + '\n' +
    ';;; based on Matrix customization system version of:\n' +
    ';;;     ' + matrix_dt + '\n' +
    ';;;\n' + format_comment_block(ch.get('comment')) + '\n' +
    ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;')

  # BUT, put the date/time of the Matrix version in Version.lsp (along
  # with the name of the language.
  global version_lsp
  version_lsp = tdl.TDLfile(os.path.join(grammar_path, 'Version.lsp'))

  version_lsp.add_literal('(in-package :common-lisp-user)\n\n' +
                          '(defparameter *grammar-version* \"' +
                          ch.get('language') + ' (' + lisp_dt + ')\")')

  # Initialize various type hierarchies
  case.init_case_hierarchy(ch, hierarchies)
 # init_person_hierarchy()
 # init_number_hierarchy()
 # init_pernum_hierarchy()
 # init_gender_hierarchy()
 # init_other_hierarchies()
  agreement_features.init_agreement_hierarchies(ch, hierarchies)
 # init_tense_hierarchy()
 # init_aspect_hierarchy()
 # init_situation_hierarchy()
 # init_mood_hierarchy()
 # init_form_hierarchy()
  verbal_features.init_verbal_hierarchies(ch, hierarchies)

  #Integrate choices related to lexical entries imported from
  #Toolbox lexicon file(s), if any.  NOTE: This needs to be called
  #before anything else that looks at the lexicon-related choices,
  #so before lexical_items.insert_ids().
  toolboximport.integrate_imported_entries(ch)

  #Create unique ids for each lexical entry; this allows
  #us to do the same merging on the lexicon TDL file as we
  #do on the other TDL files.  NOTE: This needs to be called
  #before customize_lexicon() and customize_inflection()
  lexical_items.insert_ids(ch)

  # The following might modify hierarchies in some way, so it's best
  # to customize those components and only have them contribute their
  # information to lexical rules when we customize inflection.
  

  lexical_items.customize_lexicon(mylang, ch, lexicon, trigger, hierarchies, lrules, rules, climb_files)
  argument_optionality.customize_arg_op(mylang, ch, rules, hierarchies, climb_files)
  ###DIRECT INVERSE, TODO WHEN DOING DESCRIPTION
  direct_inverse.customize_direct_inverse(ch, mylang, climb_files, hierarchies)
  case.customize_case(mylang, climb_files, ch, hierarchies)
  argument_alternation.customize_argument_alternation(ch, mylang, lrules, lexicon, climb_files)
  #argument_optionality.customize_arg_op(ch, mylang)
  # after all structures have been customized, customize inflection,
  # but provide the methods the components above have for their own
  # contributions to the lexical rules
  add_lexrules_methods = [case.add_lexrules,
                          argument_optionality.add_lexrules,
                          direct_inverse.add_lexrules]

  climb_morph = climb_files.get('morph')
  climb_morph.set_section('mylang')
  to_cfv = morphotactics.customize_inflection(ch, add_lexrules_methods,
                                              mylang, irules, lrules, lexicon, climb_morph)
  features.process_cfv_list(mylang, ch, hierarchies, to_cfv, climbfile=climb_morph)

  # Call the other customization functions
 # customize_person_and_number()
 # customize_gender()
 #  customize_other_features()
  agreement_features.customize_agreement_features(mylang, climb_files, hierarchies)
 # customize_form()
 # customize_tense()
 # customize_aspect()
 # customize_situation()
 # customize_mood()
  verbal_features.customize_verbal_features(mylang, climb_files, hierarchies)
  word_order.customize_word_order(mylang, ch, rules, climb_files)
###call specialized Germanic word order rules:
  if ch.get('word-order') == 'v2' and ch.get('verb-cluster') == 'yes':
    word_order_v2_vcluster.v2_and_verbal_clusters(ch, mylang, lrules, rules, climb_files)
 #climb dict continue here
  negation.customize_sentential_negation(mylang, ch, lexicon, rules, lrules, climb_files)
  coordination.customize_coordination(mylang, ch, lexicon, rules, irules, climb_files)
  yes_no_questions.customize_yesno_questions(mylang, ch, rules, lrules, hierarchies, climb_files)
  if ch.get('passivization') == 'yes':
    passivization.customize_passivization(ch, mylang, lrules, lexicon, trigger, climb_files)
  if ch.get('ldd') == 'yes':
    long_distance_dependencies.customize_long_distance_deps(ch, mylang, rules, climb_files)
  if ch.get('extraposition') == 'yes':
    extraposition.create_extraposition(ch, mylang, rules, climb_files)
  if ch.get('comparatives') == 'yes':
    comparatives.create_comparative_basic_type(ch, mylang, lexicon, trigger, climb_files)
  customize_punctuation(grammar_path)
  customize_test_sentences(grammar_path)
  customize_itsdb(grammar_path)
  customize_script(grammar_path)
  customize_pettdl(grammar_path)
  customize_acetdl(grammar_path)
  customize_roots(grammar_path)

  # Save the output files
  mylang.save()
  rules.save()
  irules.save()
  lrules.save()
  lexicon.save()
  roots.save()
  trigger.save()
  version_lsp.save()

  for cl_file in climb_files.itervalues():
    cl_file.save()

  #here feature geometry will be created
  if not ch.get('subcat_list') == 'tiger-complete' and ch.get('shortclimb') == 'yes':
    flop_file = grammar_path +  '/' + ch.get('language').lower() + '-pet.tdl'
    extract_feature_geometry.extract_feature_geometry(flop_file)
    abbreviate_paths_in_climb.abbreviate_paths(grammar_path + '/climb/')
  #here path reduction will be applied to files in climb


  # Setup version control, if any
  setup_vcs(ch, grammar_path)

  return grammar_path

def get_climb_path():
  # customizationroot is only set for local use. The installation for
  # the questionnaire does not use it.
  cr = os.environ.get('CUSTOMIZATIONROOT','')
  if cr: cr = os.path.join(cr, '..')
  return os.path.join(cr, 'climb')

def get_matrix_core_path():
  # customizationroot is only set for local use. The installation for
  # the questionnaire does not use it.
  cr = os.environ.get('CUSTOMIZATIONROOT','')
  if cr: cr = os.path.join(cr, '..')
  return os.path.join(cr, 'matrix-core')

def get_grammar_path(isocode, language, destination):
  '''
  Using the language or iso-code, get a unique pathname
  for the grammar directory.
  '''
  # three possibilities for dir names. If all are taken, raise an exception
  for dir_name in [isocode, language, isocode + '_grammar']:
    if dir_name == '': continue
    grammar_path = os.path.join(destination, dir_name.replace(' ', '_'))
    # if grammar_path already exists as a file, it is likely the choices file
    if not (os.path.exists(grammar_path) and os.path.isfile(grammar_path)):
      return grammar_path
  raise Exception("Grammar directory not available.")

###############################################################
# Allow customize_matrix() to be called directly from the
# command line or shell scripts.

if __name__ == "__main__":
  customize_matrix(sys.argv[1], 'tgz')
