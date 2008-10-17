;;;
;;; this file should be `Index.lisp' and reside in the directory containing the
;;; tsdb(1) test suite skeleton databases (typically a subdirectory `skeletons'
;;; in the tsdb(1) database root directory `*tsdb-home*').
;;;
;;; the file should contain a single un-quote()d Common-Lisp list enumerating
;;; the available skeletons, e.g.
;;;
;;;   (((:path . "english") (:content . "English TSNLP test suite"))
;;;    ((:path . "csli") (:content . "CSLI (ERGO) test suite"))
;;;    ((:path . "vm") (:content . "English VerbMobil data")))
;;;
;;; where the individual entries are assoc() lists with at least two elements:
;;;
;;;   - :path --- the (relative) directory name containing the skeleton;
;;;   - :content --- a descriptive comment.
;;;
;;; the order of entries is irrelevant as the `tsdb :skeletons' command sorts
;;; the list lexicographically before output.
;;;

(
((:path . "tiniest") (:content . "tiniest: A very basic grammar just to get the unit tests started.  SOV word order, no frills."))
 ;;; new-unit-test-here
((:path . "nf-twoforms-withtwoaux-vp-1008") (:content . "nf-twoforms-withtwoaux-vp-1008: testing-- two nonfinite forms"))
((:path . "nf-form-withaux-vp-1008") (:content . "nf-form-withaux-vp-1008: testing nonfinite form constraint for aux complement"))
((:path . "fin-forms-noaux-1008") (:content . "fin-forms-noaux-1008: testing finite/nonfinite distinction when there are no auxiliaries"))
((:path . "auxcomp-markfeature-vp-1015") (:content . "auxcomp-markfeature-vp-1015: testing KEYS.KEY mhat is being used to distinguish etre and avoir type auxiliary verb classes"))
((:path . "auxcomp-feature-engstative-vp-1013") (:content . "auxcomp-feature-engstative-vp-1013: testing verb class feature stative and aux constrained to nonstative"))
((:path . "noaux-toblig-aopt-onv") (:content . "noaux-toblig-aopt-onv: obligatory tense, optional aspect on v, no aux level 3 test"))
((:path . "auxten-vpcompnfasp-tafeat") (:content . "auxten-vpcompnfasp-tafeat: tensed auxilialevel 3 test"))
((:path . "nopaux-noinfl-vpcomp-f-formfeat") (:content . "nopaux-noinfl-vpcomp-f-formfeat: single uninflected aux with finite vp complement, level 2 test (inflection but no t&a features)"))
((:path . "aux-f-vpcomp-nfconst-formfeat") (:content . "aux-f-vpcomp-nfconst-formfeat: finite auxes with nf vp compleof the nf comp is constrained - level 2 test (inflection, no t&a features)"))
((:path . "aux-v-f-noinfl") (:content . "aux-v-f-noinfl: two aux, finite v vomp, no inflection, level 1 test"))
((:path . "aux-vp-f-noinfl") (:content . "aux-vp-f-noinfl: two aux, finite vp comp, no inflection, level 1 test"))
((:path . "aux-s-f-noinfl") (:content . "aux-s-f-noinfl: two aux, finite sentential compelement, no inflection, level1 test"))
((:path . "testingcompforms") (:content . "testingcompforms: small ts - known problems"))
((:path . "dir-inv-fore") (:content . "dir-inv-fore: Direct-inverse, pseudo-Fore"))
((:path . "dir-inv-algonquian") (:content . "dir-inv-algonquian: Direct-inverse, pseudo-Algonquian"))
((:path . "case-tripartite") (:content . "case-tripartite: Case, tripartite"))
((:path . "case-split-v") (:content . "case-split-v: Case, split-V"))
((:path . "case-split-s") (:content . "case-split-s: Case, split-S"))
((:path . "case-split-n") (:content . "case-split-n: Case, split-N"))
((:path . "case-none") (:content . "case-none: Case, none"))
((:path . "case-nom-acc-adp") (:content . "case-nom-acc-adp: Case, nominative-accusative w/ adpositions"))
((:path . "case-nom-acc") (:content . "case-nom-acc: Case, nominative-accusative"))
((:path . "case-focus") (:content . "case-focus: Case, focus"))
((:path . "case-fluid-s") (:content . "case-fluid-s: Case, fluid-S"))
((:path . "case-erg-abs") (:content . "case-erg-abs: Case, ergative-absolutive"))
 )
