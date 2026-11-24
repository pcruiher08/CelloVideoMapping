{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 1,
            "revision": 5,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 0.0, 0.0, 1700.0, 780.0 ],
        "boxes": [
            {
                "box": {
                    "id": "title",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 25.0, 15.0, 420.0, 20.0 ],
                    "text": "CELLO FX RIG   /   MAX 9"
                }
            },
            {
                "box": {
                    "id": "sub",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 25.0, 48.0, 640.0, 20.0 ],
                    "text": "FLAT PATCH • direct audio wiring • set device in Audio Status"
                }
            },
            {
                "box": {
                    "id": "masterhead",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 25.0, 84.0, 260.0, 20.0 ],
                    "text": "I/O  +  SIGNAL TEST"
                }
            },
            {
                "box": {
                    "id": "dsp",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 25.0, 112.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "dspl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 56.0, 112.0, 55.0, 20.0 ],
                    "text": "DSP"
                }
            },
            {
                "box": {
                    "id": "dspmsg",
                    "linecount": 2,
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 25.0, 145.0, 45.0, 35.0 ],
                    "text": ";\rdsp $1"
                }
            },
            {
                "box": {
                    "id": "adc",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 25.0, 195.0, 70.0, 22.0 ],
                    "text": "adc~ 1"
                }
            },
            {
                "box": {
                    "id": "testosc",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 110.0, 195.0, 90.0, 22.0 ],
                    "text": "cycle~ 220"
                }
            },
            {
                "box": {
                    "id": "teston",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 110.0, 165.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "testlabel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 142.0339059829712, 173.8813600540161, 330.0, 20.0 ],
                    "text": "TEST TONE (switch on to validate DSP path)"
                }
            },
            {
                "box": {
                    "id": "testgain",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 110.0, 225.0, 50.0, 22.0 ],
                    "text": "*~ 0.08"
                }
            },
            {
                "box": {
                    "id": "source",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 55.0, 260.0, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "inputgain",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 25.0, 300.0, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "ig",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 90.0, 300.0, 110.0, 20.0 ],
                    "text": "INPUT GAIN"
                }
            },
            {
                "box": {
                    "id": "ing",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 55.0, 335.0, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "wh",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 250.0, 84.0, 270.0, 20.0 ],
                    "text": "02  WHAMMY"
                }
            },
            {
                "box": {
                    "id": "ps",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "" ],
                    "patching_rect": [ 322.0339059829712, 195.05084943771362, 120.0, 22.0 ],
                    "text": "pitchshift~ 1"
                }
            },
            {
                "box": {
                    "id": "expr",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 322.0339059829712, 150.983051776886, 355.0, 22.0 ],
                    "text": "expr pow(2.\\, (($f1 * ($f3 - $f2)) + $f2) / 12.)"
                }
            },
            {
                "box": {
                    "id": "exprctrl",
                    "maxclass": "dial",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 322.0339059829712, 112.0, 62.0, 62.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "low",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 398.30509424209595, 112.0, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "high",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 462.7118754386902, 112.0, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "ranges",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 903.3898520469666, 106.77966356277466, 190.0, 20.0 ],
                    "text": "RANGE ST / LOW / HIGH"
                }
            },
            {
                "box": {
                    "id": "rat",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 322.0339059829712, 225.55932474136353, 65.0, 22.0 ],
                    "text": "sig~ 1."
                }
            },
            {
                "box": {
                    "id": "wetps",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 322.0339059829712, 266.23729181289673, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "dryps",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 393.2203483581543, 266.23729181289673, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "whmix",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 493.2203507423401, 195.05084943771362, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "whmixl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 562.711877822876, 195.05084943771362, 90.0, 20.0 ],
                    "text": "WET 0–1"
                }
            },
            {
                "box": {
                    "id": "whdry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 493.2203507423401, 225.55932474136353, 55.0, 22.0 ],
                    "text": "!- 1."
                }
            },
            {
                "box": {
                    "id": "whsum",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 352.5423812866211, 305.2203435897827, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "whgain",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 322.0339059829712, 371.32204008102417, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "whbypass",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 393.2203483581543, 340.81356477737427, 250.0, 20.0 ],
                    "text": "WHAMMY WET / BYPASS = 0"
                }
            },
            {
                "box": {
                    "id": "dh",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1042.3729062080383, 77.96610355377197, 270.0, 20.0 ],
                    "text": "03  DELAY"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "dtime",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1042.3729062080383, 106.77966356277466, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "dtl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1111.8644332885742, 106.77966356277466, 190.0, 20.0 ],
                    "text": "TIME ms (20–8000)"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "dfb",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1042.3729062080383, 138.98305416107178, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "dfbl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1111.8644332885742, 138.98305416107178, 225.0, 20.0 ],
                    "text": "FEEDBACK (clamped ≤0.9)"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "dmix",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1042.3729062080383, 172.8813600540161, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "dml",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1111.8644332885742, 172.8813600540161, 220.0, 20.0 ],
                    "text": "WET 0–1 / BYPASS = 0"
                }
            },
            {
                "box": {
                    "id": "delayin",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1042.3729062080383, 218.64407300949097, 180.0, 20.0 ],
                    "text": "WHAMMY OUT → DELAY"
                }
            },
            {
                "box": {
                    "id": "tapin",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "tapconnect" ],
                    "patching_rect": [ 1042.3729062080383, 318.64407539367676, 95.0, 22.0 ],
                    "text": "tapin~ 8000"
                }
            },
            {
                "box": {
                    "id": "tapout",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1042.3729062080383, 374.5762801170349, 100.0, 22.0 ],
                    "text": "tapout~ 420"
                }
            },
            {
                "box": {
                    "id": "dlp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1203.389859199524, 374.5762801170349, 105.0, 22.0 ],
                    "text": "onepole~ 6000"
                }
            },
            {
                "box": {
                    "id": "dhp",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 4,
                    "outlettype": [ "signal", "signal", "signal", "signal" ],
                    "patching_rect": [ 1203.389859199524, 413.5593318939209, 75.0, 22.0 ],
                    "text": "svf~ 120 0.3"
                }
            },
            {
                "box": {
                    "id": "dclip",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1203.389859199524, 454.2372989654541, 120.0, 22.0 ],
                    "text": "clip~ -0.8 0.8"
                }
            },
            {
                "box": {
                    "id": "damp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1203.389859199524, 494.9152660369873, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "dline",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "bang" ],
                    "patching_rect": [ 1042.3729062080383, 279.66102361679077, 60.0, 22.0 ],
                    "text": "line~"
                }
            },
            {
                "box": {
                    "id": "dtimepack",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1042.3729062080383, 244.06780242919922, 100.0, 22.0 ],
                    "text": "pack 0. 80."
                }
            },
            {
                "box": {
                    "id": "dfeedback",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1242.37291097641, 279.66102361679077, 100.0, 22.0 ],
                    "text": "clip 0. 0.9"
                }
            },
            {
                "box": {
                    "id": "dfbsig",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1542.881395816803, 433.8983154296875, 50.0, 22.0 ],
                    "text": "sig~"
                }
            },
            {
                "box": {
                    "id": "dsum",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1083.0508732795715, 538.9830636978149, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "dwet",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1042.3729062080383, 494.9152660369873, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "ddry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1122.0339250564575, 494.9152660369873, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "dcomp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1122.0339250564575, 454.2372989654541, 55.0, 22.0 ],
                    "text": "!- 1."
                }
            },
            {
                "box": {
                    "id": "doutgain",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1042.3729062080383, 605.0847601890564, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "doutlabel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1111.8644332885742, 574.5762848854065, 130.0, 20.0 ],
                    "text": "DELAY OUTPUT"
                }
            },
            {
                "box": {
                    "id": "sh",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1561.5254640579224, 232.2033953666687, 350.0, 20.0 ],
                    "text": "01  SUSTAIN  /  captures delay output"
                }
            },
            {
                "box": {
                    "id": "capture",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.5254640579224, 261.0169553756714, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "capturelabel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1592.0339393615723, 261.0169553756714, 130.0, 20.0 ],
                    "text": "CAPTURE 5 s"
                }
            },
            {
                "box": {
                    "id": "capttrig",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "bang" ],
                    "patching_rect": [ 1561.5254640579224, 293.2203459739685, 55.0, 22.0 ],
                    "text": "t b b"
                }
            },
            {
                "box": {
                    "id": "rec_on",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1561.5254640579224, 328.81356716156006, 60.0, 22.0 ],
                    "text": "1"
                }
            },
            {
                "box": {
                    "id": "rectimer",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 1642.8813982009888, 293.2203459739685, 85.0, 22.0 ],
                    "text": "delay 5000"
                }
            },
            {
                "box": {
                    "id": "rec_off",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1642.8813982009888, 328.81356716156006, 60.0, 22.0 ],
                    "text": "0"
                }
            },
            {
                "box": {
                    "id": "holdbuf",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 1742.8814005851746, 293.2203459739685, 210.0, 22.0 ],
                    "text": "buffer~ #0_cello_hold 5000 1"
                }
            },
            {
                "box": {
                    "id": "rec",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.5254640579224, 377.96611070632935, 165.0, 22.0 ],
                    "text": "record~ #0_cello_hold"
                }
            },
            {
                "box": {
                    "id": "groove",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 1561.5254640579224, 423.7288236618042, 220.0, 22.0 ],
                    "text": "groove~ #0_cello_hold 1 @loop 1"
                }
            },
            {
                "box": {
                    "id": "hold",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.5254640579224, 462.7118754386902, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "holdlabel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1592.0339393615723, 462.7118754386902, 160.0, 20.0 ],
                    "text": "FREEZE / RELEASE"
                }
            },
            {
                "box": {
                    "id": "holdsel",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 3,
                    "outlettype": [ "bang", "bang", "" ],
                    "patching_rect": [ 1561.5254640579224, 498.30509662628174, 65.0, 22.0 ],
                    "text": "sel 0 1"
                }
            },
            {
                "box": {
                    "id": "holdstop",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1561.5254640579224, 528.8135719299316, 60.0, 22.0 ],
                    "text": "stop"
                }
            },
            {
                "box": {
                    "id": "holdstart",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1632.7119064331055, 528.8135719299316, 60.0, 22.0 ],
                    "text": "start"
                }
            },
            {
                "box": {
                    "id": "hfade",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1722.542417049408, 498.30509662628174, 100.0, 22.0 ],
                    "text": "pack 0. 400."
                }
            },
            {
                "box": {
                    "id": "hline",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "bang" ],
                    "patching_rect": [ 1722.542417049408, 533.8983178138733, 60.0, 22.0 ],
                    "text": "line~"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "smix",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.5254640579224, 567.7966237068176, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "sml",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1632.7119064331055, 567.7966237068176, 170.0, 20.0 ],
                    "text": "SUSTAIN WET 0–1"
                }
            },
            {
                "box": {
                    "id": "hwet",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.5254640579224, 608.4745907783508, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "hdry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1642.8813982009888, 608.4745907783508, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "hcomp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1642.8813982009888, 577.9661154747009, 50.0, 22.0 ],
                    "text": "!- 1."
                }
            },
            {
                "box": {
                    "id": "hsum",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1592.0339393615723, 649.152557849884, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "hgain",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.5254640579224, 713.5593390464783, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "hlabel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1632.7119064331055, 683.0508637428284, 240.0, 20.0 ],
                    "text": "RELEASE USES 400 ms RAMP"
                }
            },
            {
                "box": {
                    "id": "rh",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1561.0169863700867, 779.6610355377197, 360.0, 20.0 ],
                    "text": "04  REVERB  /  diffuse ambience"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "rmix",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.0169863700867, 808.4745955467224, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "rml",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1632.2034287452698, 808.4745955467224, 215.0, 20.0 ],
                    "text": "WET 0–1 / BYPASS = 0"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "rsize",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.0169863700867, 840.6779861450195, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "rsizel",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1632.2034287452698, 840.6779861450195, 220.0, 20.0 ],
                    "text": "FEEDBACK / SIZE ≤ 0.85"
                }
            },
            {
                "box": {
                    "id": "revinput",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1561.0169863700867, 894.9152755737305, 210.0, 20.0 ],
                    "text": "SUSTAIN OUT → REVERB"
                }
            },
            {
                "box": {
                    "id": "rin1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.0169863700867, 940.6779885292053, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "rin2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1691.5254640579224, 940.6779885292053, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "rtap1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "tapconnect" ],
                    "patching_rect": [ 1561.0169863700867, 981.3559556007385, 90.0, 22.0 ],
                    "text": "tapin~ 300"
                }
            },
            {
                "box": {
                    "id": "rtap2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "tapconnect" ],
                    "patching_rect": [ 1691.5254640579224, 981.3559556007385, 90.0, 22.0 ],
                    "text": "tapin~ 400"
                }
            },
            {
                "box": {
                    "id": "rout1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.0169863700867, 1020.3390073776245, 90.0, 22.0 ],
                    "text": "tapout~ 31"
                }
            },
            {
                "box": {
                    "id": "rout2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1691.5254640579224, 1020.3390073776245, 90.0, 22.0 ],
                    "text": "tapout~ 43"
                }
            },
            {
                "box": {
                    "id": "rdamp1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.0169863700867, 1061.0169744491577, 105.0, 22.0 ],
                    "text": "onepole~ 5000"
                }
            },
            {
                "box": {
                    "id": "rdamp2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1691.5254640579224, 1061.0169744491577, 105.0, 22.0 ],
                    "text": "onepole~ 5000"
                }
            },
            {
                "box": {
                    "id": "rg1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.0169863700867, 1100.0000262260437, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "rg2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1691.5254640579224, 1100.0000262260437, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "rsum",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1622.0339369773865, 1140.677993297577, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "rwet",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1561.0169863700867, 1181.35596036911, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "rdry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1640.6780052185059, 1181.35596036911, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "rcomp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1640.6780052185059, 1150.8474850654602, 55.0, 22.0 ],
                    "text": "!- 1."
                }
            },
            {
                "box": {
                    "id": "rsafe",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1622.0339369773865, 1220.339012145996, 130.0, 22.0 ],
                    "text": "clip~ -0.95 0.95"
                }
            },
            {
                "box": {
                    "id": "mastergain",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1622.0339369773865, 1255.9322333335876, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "mvol",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1561.0169863700867, 1255.9322333335876, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "mvolc",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1632.2034287452698, 1286.4407086372375, 100.0, 20.0 ],
                    "text": "MASTER"
                }
            },
            {
                "box": {
                    "id": "meter",
                    "maxclass": "meter~",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 1740.6780076026917, 1255.9322333335876, 80.0, 13.0 ]
                }
            },
            {
                "box": {
                    "id": "dac",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "patching_rect": [ 1622.0339369773865, 1325.4237604141235, 85.0, 22.0 ],
                    "text": "dac~ 1 2"
                }
            },
            {
                "box": {
                    "id": "outmeter",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1740.6780076026917, 1286.4407086372375, 130.0, 20.0 ],
                    "text": "OUTPUT METER"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "whlevel",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 393.2203483581543, 371.32204008102417, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "dlevel",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1111.8644332885742, 605.0847601890564, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "slevel",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1632.7119064331055, 713.5593390464783, 58.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "dfeed",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1042.3729062080383, 289.8305153846741, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "hwetamp",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1702.2034335136414, 608.4745907783508, 50.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "rvsum",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1622.0339369773865, 1205.0847744941711, 50.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "pitscale",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 322.0339059829712, 179.79661178588867, 150.0, 22.0 ],
                    "text": "scale 0 127 0. 1."
                }
            },
            {
                "box": {
                    "id": "ccwhammy",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 25.0, 670.0, 95.0, 22.0 ],
                    "text": "ctlin 21"
                }
            },
            {
                "box": {
                    "id": "ccfb",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 130.0, 670.0, 95.0, 22.0 ],
                    "text": "ctlin 22"
                }
            },
            {
                "box": {
                    "id": "cctime",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 235.0, 670.0, 95.0, 22.0 ],
                    "text": "ctlin 23"
                }
            },
            {
                "box": {
                    "id": "ccrev",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 340.0, 670.0, 95.0, 22.0 ],
                    "text": "ctlin 24"
                }
            },
            {
                "box": {
                    "id": "ccmaster",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 445.0, 670.0, 95.0, 22.0 ],
                    "text": "ctlin 7"
                }
            },
            {
                "box": {
                    "id": "init_inputgain",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20.0, 730.0, 105.0, 22.0 ],
                    "text": "loadmess 0.5"
                }
            },
            {
                "box": {
                    "id": "init_low",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 210.0, 730.0, 105.0, 22.0 ],
                    "text": "loadmess -12"
                }
            },
            {
                "box": {
                    "id": "init_high",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 400.0, 730.0, 105.0, 22.0 ],
                    "text": "loadmess 12"
                }
            },
            {
                "box": {
                    "id": "init_whmix",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 590.0, 730.0, 105.0, 22.0 ],
                    "text": "loadmess 1"
                }
            },
            {
                "box": {
                    "id": "init_whlevel",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 780.0, 730.0, 105.0, 22.0 ],
                    "text": "loadmess 1"
                }
            },
            {
                "box": {
                    "id": "init_dtime",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1425.4237627983093, 820.3390026092529, 105.0, 22.0 ],
                    "text": "loadmess 420"
                }
            },
            {
                "box": {
                    "id": "init_dfb",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1418.6441016197205, 1186.4407062530518, 105.0, 22.0 ],
                    "text": "loadmess 0.35"
                }
            },
            {
                "box": {
                    "id": "init_dmix",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 20.0, 755.0, 105.0, 22.0 ],
                    "text": "loadmess 0.3"
                }
            },
            {
                "box": {
                    "id": "init_dlevel",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 210.0, 755.0, 105.0, 22.0 ],
                    "text": "loadmess 1"
                }
            },
            {
                "box": {
                    "id": "init_smix",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 400.0, 755.0, 105.0, 22.0 ],
                    "text": "loadmess 0.65"
                }
            },
            {
                "box": {
                    "id": "init_slevel",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 590.0, 755.0, 105.0, 22.0 ],
                    "text": "loadmess 1"
                }
            },
            {
                "box": {
                    "id": "init_rmix",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 780.0, 755.0, 105.0, 22.0 ],
                    "text": "loadmess 0.25"
                }
            },
            {
                "box": {
                    "id": "init_rsize",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1425.4237627983093, 844.067816734314, 105.0, 22.0 ],
                    "text": "loadmess 0.68"
                }
            },
            {
                "box": {
                    "id": "init_mvol",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1418.6441016197205, 1210.1695203781128, 105.0, 22.0 ],
                    "text": "loadmess 0.05"
                }
            },
            {
                "box": {
                    "id": "poll",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 25.0, 385.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "pollmetro",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 55.0, 385.0, 75.0, 22.0 ],
                    "text": "metro 100"
                }
            },
            {
                "box": {
                    "id": "snap",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 145.0, 385.0, 75.0, 22.0 ],
                    "text": "snapshot~"
                }
            },
            {
                "box": {
                    "id": "snapnum",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 235.0, 386.0, 70.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "pollcomment",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 398.30509424209595, 398.44068479537964, 430.0, 20.0 ],
                    "text": "OUTPUT LEVEL SAMPLE (non-zero confirms live DSP path)"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "source", 0 ],
                    "source": [ "adc", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rec_on", 0 ],
                    "source": [ "capttrig", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rectimer", 0 ],
                    "source": [ "capttrig", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "capttrig", 0 ],
                    "source": [ "capture", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfb", 0 ],
                    "source": [ "ccfb", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "mvol", 0 ],
                    "source": [ "ccmaster", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rmix", 0 ],
                    "source": [ "ccrev", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dtime", 0 ],
                    "source": [ "cctime", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "exprctrl", 0 ],
                    "source": [ "ccwhammy", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfeed", 1 ],
                    "source": [ "damp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "damp", 0 ],
                    "order": 0,
                    "source": [ "dclip", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dwet", 0 ],
                    "order": 1,
                    "source": [ "dclip", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ddry", 1 ],
                    "source": [ "dcomp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dsum", 1 ],
                    "source": [ "ddry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfeedback", 0 ],
                    "source": [ "dfb", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "damp", 1 ],
                    "source": [ "dfbsig", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "tapin", 0 ],
                    "source": [ "dfeed", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfbsig", 0 ],
                    "source": [ "dfeedback", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dclip", 0 ],
                    "source": [ "dhp", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "doutgain", 1 ],
                    "source": [ "dlevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "tapout", 0 ],
                    "source": [ "dline", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dhp", 0 ],
                    "source": [ "dlp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dcomp", 0 ],
                    "order": 0,
                    "source": [ "dmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dwet", 1 ],
                    "order": 1,
                    "source": [ "dmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hdry", 0 ],
                    "order": 0,
                    "source": [ "doutgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rec", 0 ],
                    "order": 1,
                    "source": [ "doutgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whsum", 1 ],
                    "source": [ "dryps", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dspmsg", 0 ],
                    "source": [ "dsp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "doutgain", 0 ],
                    "source": [ "dsum", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dtimepack", 0 ],
                    "source": [ "dtime", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dline", 0 ],
                    "source": [ "dtimepack", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dsum", 1 ],
                    "source": [ "dwet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rat", 0 ],
                    "source": [ "expr", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "pitscale", 0 ],
                    "source": [ "exprctrl", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hwet", 0 ],
                    "source": [ "groove", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hdry", 1 ],
                    "source": [ "hcomp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hsum", 1 ],
                    "source": [ "hdry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hline", 0 ],
                    "source": [ "hfade", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rdry", 0 ],
                    "order": 1,
                    "source": [ "hgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rin1", 0 ],
                    "order": 2,
                    "source": [ "hgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rin2", 0 ],
                    "order": 0,
                    "source": [ "hgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "expr", 2 ],
                    "source": [ "high", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hwetamp", 0 ],
                    "source": [ "hline", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hfade", 0 ],
                    "order": 0,
                    "source": [ "hold", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "holdsel", 0 ],
                    "order": 1,
                    "source": [ "hold", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "holdstart", 0 ],
                    "source": [ "holdsel", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "holdstop", 0 ],
                    "source": [ "holdsel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "groove", 0 ],
                    "source": [ "holdstart", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "groove", 0 ],
                    "source": [ "holdstop", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hgain", 0 ],
                    "source": [ "hsum", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hsum", 0 ],
                    "source": [ "hwet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hwet", 1 ],
                    "source": [ "hwetamp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dryps", 0 ],
                    "order": 0,
                    "source": [ "ing", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ps", 0 ],
                    "order": 1,
                    "source": [ "ing", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfb", 0 ],
                    "source": [ "init_dfb", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dlevel", 0 ],
                    "source": [ "init_dlevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dmix", 0 ],
                    "source": [ "init_dmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dtime", 0 ],
                    "source": [ "init_dtime", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "high", 0 ],
                    "source": [ "init_high", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "inputgain", 0 ],
                    "source": [ "init_inputgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "low", 0 ],
                    "source": [ "init_low", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "mvol", 0 ],
                    "source": [ "init_mvol", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rmix", 0 ],
                    "source": [ "init_rmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rsize", 0 ],
                    "source": [ "init_rsize", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "slevel", 0 ],
                    "source": [ "init_slevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "smix", 0 ],
                    "source": [ "init_smix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whlevel", 0 ],
                    "source": [ "init_whlevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whmix", 0 ],
                    "source": [ "init_whmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ing", 1 ],
                    "source": [ "inputgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "expr", 1 ],
                    "source": [ "low", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dac", 1 ],
                    "order": 1,
                    "source": [ "mastergain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dac", 0 ],
                    "order": 2,
                    "source": [ "mastergain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "meter", 0 ],
                    "order": 0,
                    "source": [ "mastergain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "snap", 0 ],
                    "order": 3,
                    "source": [ "mastergain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "mastergain", 1 ],
                    "source": [ "mvol", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "expr", 0 ],
                    "source": [ "pitscale", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "pollmetro", 0 ],
                    "source": [ "poll", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "snap", 1 ],
                    "source": [ "pollmetro", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "wetps", 0 ],
                    "source": [ "ps", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ps", 1 ],
                    "source": [ "rat", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rdry", 1 ],
                    "source": [ "rcomp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rg1", 0 ],
                    "source": [ "rdamp1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rg2", 0 ],
                    "source": [ "rdamp2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rvsum", 1 ],
                    "source": [ "rdry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rec", 0 ],
                    "source": [ "rec_off", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rec", 0 ],
                    "source": [ "rec_on", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rec_off", 0 ],
                    "source": [ "rectimer", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rin1", 1 ],
                    "source": [ "rg1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rin2", 1 ],
                    "source": [ "rg2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rtap1", 0 ],
                    "source": [ "rin1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rtap2", 0 ],
                    "source": [ "rin2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rcomp", 0 ],
                    "order": 0,
                    "source": [ "rmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rwet", 1 ],
                    "order": 1,
                    "source": [ "rmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rdamp1", 0 ],
                    "order": 1,
                    "source": [ "rout1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rsum", 0 ],
                    "order": 0,
                    "source": [ "rout1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rdamp2", 0 ],
                    "order": 0,
                    "source": [ "rout2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rsum", 1 ],
                    "order": 1,
                    "source": [ "rout2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "mastergain", 0 ],
                    "source": [ "rsafe", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rg1", 1 ],
                    "order": 1,
                    "source": [ "rsize", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rg2", 1 ],
                    "order": 0,
                    "source": [ "rsize", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rwet", 0 ],
                    "source": [ "rsum", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rout1", 0 ],
                    "source": [ "rtap1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rout2", 0 ],
                    "source": [ "rtap2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rsafe", 0 ],
                    "source": [ "rvsum", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rvsum", 0 ],
                    "source": [ "rwet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hgain", 1 ],
                    "source": [ "slevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hcomp", 0 ],
                    "order": 1,
                    "source": [ "smix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "hwetamp", 1 ],
                    "order": 0,
                    "source": [ "smix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "snapnum", 0 ],
                    "source": [ "snap", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ing", 0 ],
                    "source": [ "source", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "tapout", 0 ],
                    "source": [ "tapin", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dlp", 0 ],
                    "source": [ "tapout", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "source", 1 ],
                    "source": [ "testgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "testgain", 1 ],
                    "source": [ "teston", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "testgain", 0 ],
                    "source": [ "testosc", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whsum", 0 ],
                    "source": [ "wetps", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dryps", 1 ],
                    "source": [ "whdry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "ddry", 0 ],
                    "order": 0,
                    "source": [ "whgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dfeed", 0 ],
                    "order": 2,
                    "source": [ "whgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "dsum", 0 ],
                    "order": 1,
                    "source": [ "whgain", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whgain", 1 ],
                    "source": [ "whlevel", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "wetps", 1 ],
                    "order": 1,
                    "source": [ "whmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whdry", 0 ],
                    "order": 0,
                    "source": [ "whmix", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "whgain", 0 ],
                    "source": [ "whsum", 0 ]
                }
            }
        ],
        "autosave": 0
    }
}