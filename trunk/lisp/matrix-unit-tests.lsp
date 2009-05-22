;;; ERB 2008-06-30

;;; Function for creating unit tests for
;;; matrix developers.  Usage:

;;; Make sure your .lkbrc defines the variable
;;; *customization-root* to point to the direcotry
;;; which contains the version of customize.py
;;; you wish to test, e.g.:

; (defparameter *customization-root* "~/lingo/grammars/matrix/customize/")

;;; Invoke this from within the *common-lisp* buffer
;;; while running the lkb, as follows:

;;; (create-matrix-unit-test "choices-file" "txt-suite-file")

;;; where choices-file and txt-suite-file are names of files in
;;; the directory matrix/customize/unit-tests/scratch/.

(in-package :lkb)

(defun create-matrix-unit-test (choices-file txt-suite-file)

  ;;; Assume that these live in unit-tests/scratch, so it's not
  ;;; so annoying to type them in.
  
  (let ((choices (format nil "~a/unit-tests/scratch/~a" *customization-root* choices-file))
	(txt-suite (format nil "~a/unit-tests/scratch/~a" *customization-root* txt-suite-file)))
  
    ;;; Check to make sure files are where they should be
  
    (check-unit-test-inputs txt-suite choices)
  
    ;;; Create grammar and store in unit-tests/grammars

    (let* ((lg-name (get-language-name choices))
	   (cmd (format nil "~a~a ~a ~a ~a~a~a" 
			*customization-root* "unit-tests/call-customize"
			*customization-root* 
			choices *customization-root* "unit-tests/grammars/"
			lg-name)))
      (excl:run-shell-command cmd))
  
    ;;; Load grammar into the LKB

    (let* ((lg-name (get-language-name choices))
	   (script (format nil "~a~a~a~a"
			   *customization-root*
			   "unit-tests/grammars/"
			   lg-name
			   "/matrix/lkb/script")))
      (read-script-file-aux script))
  
    ;;; Check that [incr tsdb()] is running, and if not
    ;;; start it up:
    
    (unless (find-package :tsdb)
      (load-system "tsdb"))
    
    ;;; Set *tsdb-home* to unit-tests/home/

    (let ((home (format nil "~a~a"
			*customization-root*
			"unit-tests/home/")))
      (setf tsdb::*tsdb-home* home)
      (tsdb:tsdb :home tsdb::*tsdb-home*))
  
    ;;; Import test items

    ; directory name for profile (name is relative to *tsdb-home*)
    ; fix-me: this should maybe have timestamnp in it.
  
    (let* ((lg-name (get-language-name choices))
	   (profile-directory (format nil "current/~a" lg-name))
	   (tex-file (format nil "~a/unit-tests/logs/~a.tex" *customization-root* lg-name)))
      
      ; add profile

      (tsdb::do-import-items txt-suite profile-directory :format :ascii)
  
  
      ;;; Process all items
  
      (tsdb:tsdb :process profile-directory)
  
      ;;; It would be nice to also print out results of analyze
      ;;; coverage/overgeneration to lisp buffer ... but that 
      ;;; doesn't seem possible at present.  Instead, output them
      ;;; to a .tex file in logs/ and latex it, and open it as
      ;;; .dvi

      (let ((stream (tsdb::create-output-stream tex-file)))
	(format stream "\\documentclass[10pt]{article}~%~%\\begin{document}~%~%\\noindent~%")
	(close stream))
	  
      (tsdb::analyze-competence profile-directory :append tex-file :format :latex) 
      (tsdb::analyze-competence profile-directory :append tex-file :wf 0 :format :latex) 
      (let ((stream (tsdb::create-output-stream nil tex-file)))
	(format stream "\\end{document}~%~%")
	(close stream))
      
      (let* ((cmd1 (format nil "latex ~a.tex" lg-name))
	     (cmd2 (format nil "xdvi ~a.dvi &" lg-name)))
	(excl:chdir (format nil "~aunit-tests/logs/" *customization-root*))
	(excl:run-shell-command cmd1 :wait t)
	(excl:run-shell-command cmd2)))
    
    
      ;;; Print out instructions on how to browse results
  
    (format t "~%~%To browse the results, try Options | Update | All tsdb() status,~%then click on the new test suite and do Browse | Results~%from the [incr tsdb()] podium.~%~%If you are happy with the results, the next step~%is to invoke add-unit-test.py~%~%")))


;;; Command for interactively running one unit test.  Should
;;; leave you in a state where the grammar is loaded and the
;;; compare | detail window is open for.


(defun run-matrix-unit-test (lg-name)

  ;;; Check that *customization-root* is defined.
  
  (if (or (not (find-symbol "*CUSTOMIZATION-ROOT*"))
	  (not (boundp '*CUSTOMIZATION-ROOT*)))
      (error "No value for *customization-root*"))

  ;;; Check that a unit-test by that name exists, but not a grammar
  
  (let ((cust (make-pathname :directory *customization-root* :name "customize.py")))
    (if (fad:file-exists-p cust)
	nil
      (error "Invalid customization root: ~S" *customization-root*)))

  (let ((grammar-path (make-pathname 
		       :directory 
		       (pathname-directory 
			(dir-append *customization-root* 
				    '(:relative "unit-tests" "grammars"))) 
		       :name lg-name)))
    (if (fad:file-exists-p grammar-path)
      (error "Move ~S, it is in the way" grammar-path)))
  
  (let ((choices-path (make-pathname 
		       :directory 
		       (pathname-directory 
			(dir-append *customization-root* 
				    '(:relative "unit-tests" "choices"))) 
		       :name lg-name)))
    (if (fad:file-exists-p choices-path)
	nil
      (error "No unit test called ~S" lg-name))

    
    ;;; Customize grammar
  
    (let* ((lg-name (get-language-name choices-path))
	   (cmd (format nil "~a~a ~a ~a ~a~a~a" 
			*customization-root* "unit-tests/call-customize"
			*customization-root* 
			choices-path *customization-root* "unit-tests/grammars/"
			lg-name)))
      (excl:run-shell-command cmd))
  
  ;;; Load grammar into the LKB

    (let* ((lg-name (get-language-name choices-path))
	   (script (format nil "~a~a~a~a"
			   *customization-root*
			   "unit-tests/grammars/"
			   lg-name
			   "/matrix/lkb/script")))
      (read-script-file-aux script)))
  
  ;;; Check that [incr tsdb()] is running, and if not
  ;;; start it up:
    
  (unless (find-package :tsdb)
    (load-system "tsdb"))
    
  ;;; Set *tsdb-home* to unit-tests/home/

  (let ((home (format nil "~a~a"
		       *customization-root*
		       "unit-tests/home/")))
    (setf tsdb::*tsdb-home* home)
    (tsdb:tsdb :home tsdb::*tsdb-home*))
  
  ;;; Set *tsdb-skeleton-directory* to unit-tests/skeletons/
  

  (let ((skel (format nil "~a~a"
		      *customization-root*
		      "unit-tests/skeletons/")))
    (tsdb:tsdb :skeletons skel))
  
  ;;; Create and process profile

  (let ((target (format nil "current/~a" lg-name)))
    (tsdb:tsdb :create target :skeleton lg-name) 
    (tsdb:tsdb :process target))
  
  ;;; Do comparison
  
  (let ((gold (format nil "gold/~a" lg-name))
	(target (format nil "current/~a" lg-name))
	(log-file (format nil "~aunit-tests/logs/~a" *customization-root* lg-name)))
    (tsdb::compare-in-detail target gold 
			     :format :ascii 
			     :compare '(:readings :mrs)
			     :append log-file)
    (format t "Here are the diffs, if any, between the current and gold standard.~%")
    (excl:run-shell-command (format nil "cat ~a" log-file))
    (excl:run-shell-command (format nil "rm ~a" log-file)))
    
   ;;; Give instructions on how to open window showing results
  
  (format t "To look at these interactively, do the following in the [incr tsdb()] podium:~%")
  (format t "Update | All tsdb(1) status~%")
  (format t "Right click on gold/~a~%" lg-name)
  (format t "Left click on current/~a~%" lg-name)
  (format t "Compare | Intersection | mrs~%")
  (format t "Compare | Detail~%")
  )


(defun check-unit-test-inputs (txt-suite choices)

    ;;; Check that *customization-root* is defined.

  (if (or (not (find-symbol "*CUSTOMIZATION-ROOT*"))
	  (not (boundp '*CUSTOMIZATION-ROOT*)))
      (error "No value for *customization-root*"))
  
    
    ;;; Check path names
    
  (if (fad:file-exists-p txt-suite)
      nil
    (error "No txt-suite at path ~S." txt-suite))
  
  (if (fad:file-exists-p choices)
      nil
    (error "No choices file at path ~S." choices))
    
  (let ((cust (make-pathname :directory *customization-root* :name "customize.py")))
    (if (fad:file-exists-p cust)
	nil
      (error "Invalid customization root: ~S" *customization-root*)))
    
    ;;; Check language name from choices file and make sure
    ;;; that it isn't already in use among unit-tests and/or
    ;;; that there isn't already a grammar by that name in the
    ;;; grammars/ directory.
    
  (let* ((lg-name (get-language-name choices))
	 (choices-path (make-pathname 
			:directory 
			(pathname-directory 
			 (dir-append *customization-root* 
				     '(:relative "unit-tests" "choices"))) 
			:name lg-name))
	 (grammar-path (make-pathname 
			:directory 
			(pathname-directory 
			 (dir-append *customization-root* 
				     '(:relative "unit-tests" "grammars"))) 
			:name lg-name))
	 )
    (if (fad:file-exists-p choices-path)
	(error "A unit test with name ~S already exists.  Create a new choices file with a different language name and start again.  Or, if you wanted to run that existing unit test, use run-unit-test." lg-name))
    (if (fad:file-exists-p grammar-path)
	(error "A grammar with name ~S already exists in unit-tests/grammars. Please move it first before invoking this function." lg-name))))


(defun get-language-name (choices)

  ;;; Extract language name from choices file.
  ;;; Assume it's stored in a line that says language=name
  
  (let ((lg-name nil))
    (with-open-file (stream choices)
      (loop for line = (read-line stream nil)
	  until (eq line nil)
	  do (if (and (> (length line) 9)
		      (equal (subseq line 0 9) "language="))
		 (setf lg-name (subseq line 9)))))
    
    
    (if lg-name
	lg-name
      (error "Invalid choices file: No language name given."))))

;;; Function for cleaning up files when you're done with dealing
;;; with a unit-test interactively.  This will leave behind whatever
;;; is in choices/, txt-suites/, skeletons/, and home/gold/, but
;;; clean up in grammars/, logs/, and home/current/ so you can run again.
;;; Possible improvement: Flag for just moving those out of the way for
;;; further comparison.

(defun clean-up-unit-test (lg-name)
  
  (let ((path (format nil "~aunit-tests" *customization-root*)))
  
  ;;; Remove grammar
  
    (excl:run-shell-command (format nil "rm -r ~a/grammars/~a" path lg-name))
  
  ;;; Remove log files (.tex, .aux, .dvi)
    
    (excl:run-shell-command (format nil "rm ~a/logs/~a.tex" path lg-name))
    (excl:run-shell-command (format nil "rm ~a/logs/~a.aux" path lg-name))
    (excl:run-shell-command (format nil "rm ~a/logs/~a.dvi" path lg-name))
    
  ;;; Remove profile ... or not: these often can't be removed, and
  ;;; get over-written by [incr tsdb()] anyway.
    
  ;;;  (excl:run-shell-command (format nil "rm -r ~a/home/current/~a" path lg-name))
    ))