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
        "rect": [ 789.0, 95.0, 689.0, 853.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-10",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1046.8480052947998, 715.7894992828369, 201.05263876914978, 20.0 ],
                    "text": "in case of using freenectIR"
                }
            },
            {
                "box": {
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 1419.587549328804, 578.3504830598831, 48.0, 22.0 ],
                    "text": "change"
                }
            },
            {
                "box": {
                    "id": "obj-104",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 379.5192104578018, 459.6491184234619, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-105",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 379.5192104578018, 432.4675283432007, 135.0, 22.0 ],
                    "text": "prepend /audio/amptrsh"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-103",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 379.5192104578018, 407.01753997802734, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-101",
                    "maxclass": "newobj",
                    "numinlets": 5,
                    "numoutlets": 4,
                    "outlettype": [ "int", "", "", "int" ],
                    "patching_rect": [ 379.5192104578018, 380.70175075531006, 69.0, 22.0 ],
                    "text": "counter 0 2"
                }
            },
            {
                "box": {
                    "id": "obj-100",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 379.5192104578018, 353.9473650455475, 48.0, 22.0 ],
                    "text": "change"
                }
            },
            {
                "box": {
                    "id": "obj-99",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 379.5192104578018, 325.9740228652954, 36.0, 22.0 ],
                    "text": "> 0.8"
                }
            },
            {
                "box": {
                    "annotation": "## View or monitor video input ##",
                    "bgmode": 1,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "id": "obj-97",
                    "lockeddragscroll": 0,
                    "lockedsize": 0,
                    "maxclass": "bpatcher",
                    "name": "vz.viewr.maxpat",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "offset": [ 0.0, 0.0 ],
                    "patching_rect": [ 1169.6968665122986, 1018.1817283630371, 230.0, 208.0 ],
                    "prototypename": "pixl",
                    "varname": "viewr",
                    "viewvisibility": 1
                }
            },
            {
                "box": {
                    "id": "obj-92",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 986.61, 1087.45, 91.0, 22.0 ],
                    "text": "jit.gl.videoplane"
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-90",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 1046.8480052947998, 655.6961939334869, 297.4683505296707, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Infrared CAM",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-85",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1117.3913136720657, 836.2318910360336, 165.0, 22.0 ],
                    "text": "prepend /video/IR_brightness"
                }
            },
            {
                "box": {
                    "id": "obj-47",
                    "maxclass": "live.dial",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "float" ],
                    "parameter_enable": 1,
                    "patching_rect": [ 1117.41943693161, 740.5797163248062, 68.5714316368103, 48.0 ],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "IR_Brightness",
                            "parameter_mmax": 1.0,
                            "parameter_mmin": -1.0,
                            "parameter_modmode": 4,
                            "parameter_osc_name": "IDcontrast",
                            "parameter_shortname": "IR_Brightness",
                            "parameter_type": 0,
                            "parameter_unitstyle": 1
                        }
                    },
                    "varname": "live.dial[1]"
                }
            },
            {
                "box": {
                    "id": "obj-44",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1046.8480052947998, 872.463775396347, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-41",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1046.8480052947998, 806.434755384922, 153.0, 22.0 ],
                    "text": "prepend /video/IR_contrast"
                }
            },
            {
                "box": {
                    "id": "obj-14",
                    "maxclass": "live.dial",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "float" ],
                    "parameter_enable": 1,
                    "patching_rect": [ 1046.8480052947998, 740.5797163248062, 68.5714316368103, 48.0 ],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_initial": [ 0.0 ],
                            "parameter_initial_enable": 1,
                            "parameter_longname": "IR_Contrast",
                            "parameter_mmax": 3.0,
                            "parameter_modmode": 4,
                            "parameter_osc_name": "IDcontrast",
                            "parameter_shortname": "IR_Contrast",
                            "parameter_type": 0,
                            "parameter_unitstyle": 1
                        }
                    },
                    "varname": "live.dial"
                }
            },
            {
                "box": {
                    "id": "obj-115",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 774.6268379688263, 108.79220676422119, 58.0, 22.0 ],
                    "text": "loadbang"
                }
            },
            {
                "box": {
                    "id": "obj-111",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 466.5194778442383, 583.1168775558472, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-109",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 391.8181678056717, 576.6233711242676, 58.0, 22.0 ],
                    "text": "loadbang"
                }
            },
            {
                "box": {
                    "id": "obj-5",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 27.272727012634277, 490.9037996530533, 37.0, 22.0 ],
                    "text": "*~ 10"
                }
            },
            {
                "box": {
                    "id": "obj-95",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1346.0, 457.7012948989868, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-96",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1346.0, 398.7012948989868, 153.0, 22.0 ],
                    "text": "prepend /audio/freqforcolor"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-93",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1402.0617771148682, 276.28864431381226, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-91",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1357.0, 345.7532434463501, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 18.0,
                    "id": "obj-89",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 34.772727489471436, 836.3636283874512, 162.33766078948975, 32.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Audio Output",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-86",
                    "maxclass": "newobj",
                    "numinlets": 5,
                    "numoutlets": 0,
                    "patching_rect": [ 36.571428298950195, 962.3376531600952, 85.0, 22.0 ],
                    "text": "dac~ 1 2 3 4 5"
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 18.0,
                    "id": "obj-83",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 284.41558170318604, 836.3636283874512, 130.0, 32.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "OSC Output",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-62",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 1132.4675216674805, 103.89610290527344, 210.3896083831787, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "MIDI Inst.",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-60",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 519.4805145263672, 107.79220676422119, 210.3896083831787, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Vibrato",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-59",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 292.32440626621246, 518.8636312484741, 210.3896083831787, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Bandpass",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-46",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 292.32440626621246, 207.68830966949463, 210.3896083831787, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Amplitude",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-30",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 225.97402381896973, 162.33766078948975, 29.5, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 198.70129680633545, 450.64934635162354, 136.0, 22.0 ],
                    "text": "prepend /audio/intensity"
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 198.70129680633545, 479.22077465057373, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-84",
                    "maxclass": "ezadc~",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 22.077921867370605, 93.5064926147461, 45.0, 45.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-66",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "patching_rect": [ 1085.7142753601074, 316.883113861084, 47.0, 22.0 ],
                    "text": "line 0 1"
                }
            },
            {
                "box": {
                    "id": "obj-69",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1085.7142753601074, 287.01298427581787, 64.0, 22.0 ],
                    "text": "pack f 100"
                }
            },
            {
                "box": {
                    "id": "obj-39",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 1085.7142753601074, 390.9090871810913, 34.0, 22.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "obj-38",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1085.7142753601074, 346.7532434463501, 36.0, 22.0 ],
                    "text": "< 0.1"
                }
            },
            {
                "box": {
                    "id": "obj-70",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1146.7532358169556, 483.1168785095215, 29.5, 22.0 ],
                    "text": "int"
                }
            },
            {
                "box": {
                    "id": "obj-72",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1218.181806564331, 497.4025926589966, 29.5, 22.0 ],
                    "text": "int"
                }
            },
            {
                "box": {
                    "id": "obj-33",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1218.181806564331, 467.53246307373047, 39.0, 22.0 ],
                    "text": "round"
                }
            },
            {
                "box": {
                    "id": "obj-73",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 0,
                    "patching_rect": [ 1146.7532358169556, 588.3116827011108, 124.0, 22.0 ],
                    "text": "noteout \"From Max 1\""
                }
            },
            {
                "box": {
                    "id": "obj-74",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1085.7142753601074, 428.57142448425293, 35.0, 22.0 ],
                    "text": "clear"
                }
            },
            {
                "box": {
                    "id": "obj-76",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "patching_rect": [ 1251.948040008545, 287.01298427581787, 29.5, 22.0 ],
                    "text": "t l b"
                }
            },
            {
                "box": {
                    "id": "obj-28",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 1146.7532358169556, 542.8571376800537, 62.0, 22.0 ],
                    "text": "ddg.mono"
                }
            },
            {
                "box": {
                    "id": "obj-27",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1218.181806564331, 406.4935026168823, 53.0, 22.0 ],
                    "text": "clip 0. 1."
                }
            },
            {
                "box": {
                    "id": "obj-77",
                    "maxclass": "newobj",
                    "numinlets": 6,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1218.181806564331, 437.66233348846436, 97.0, 22.0 ],
                    "text": "scale 0. 1. 0 127"
                }
            },
            {
                "box": {
                    "id": "obj-78",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1146.7532358169556, 451.94804763793945, 39.0, 22.0 ],
                    "text": "round"
                }
            },
            {
                "box": {
                    "id": "obj-79",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1146.7532358169556, 414.28571033477783, 32.0, 22.0 ],
                    "text": "ftom"
                }
            },
            {
                "box": {
                    "id": "obj-80",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "float" ],
                    "patching_rect": [ 1177.9220666885376, 377.92207431793213, 61.0, 22.0 ],
                    "text": "unpack f f"
                }
            },
            {
                "box": {
                    "id": "obj-16",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 1054.5454444885254, 177.92207622528076, 30.0, 22.0 ],
                    "text": "*~ 3"
                }
            },
            {
                "box": {
                    "id": "obj-81",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 1054.5454444885254, 148.05194664001465, 81.0, 22.0 ],
                    "text": "cross~ 10000"
                }
            },
            {
                "box": {
                    "id": "obj-6",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 1054.5454444885254, 115.5844144821167, 61.0, 22.0 ],
                    "text": "cross~ 50"
                }
            },
            {
                "box": {
                    "id": "obj-82",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "float", "float", "" ],
                    "patching_rect": [ 989.9224959611893, 220.93023598194122, 566.0, 22.0 ],
                    "text": "fzero~ @onsetlist 1 @threshold 0.02 @onsetamp 0.15 @onsetpitch 1 @onsetperiod 2048 @period 1024"
                }
            },
            {
                "box": {
                    "id": "obj-61",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 142.85714149475098, 536.3636312484741, 74.0, 22.0 ],
                    "text": "cross~ 1500"
                }
            },
            {
                "box": {
                    "id": "obj-58",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 27.272727012634277, 523.3766183853149, 68.0, 22.0 ],
                    "text": "cross~ 200"
                }
            },
            {
                "box": {
                    "id": "obj-57",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 284.41558170318604, 776.623369216919, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-56",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 284.41558170318604, 738.9610319137573, 119.0, 22.0 ],
                    "text": "prepend /audio/highr"
                }
            },
            {
                "box": {
                    "id": "obj-55",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 158.441556930542, 738.9610319137573, 115.0, 22.0 ],
                    "text": "prepend /audio/midr"
                }
            },
            {
                "box": {
                    "id": "obj-54",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 28.571428298950195, 738.9610319137573, 114.0, 22.0 ],
                    "text": "prepend /audio/lowr"
                }
            },
            {
                "box": {
                    "id": "obj-52",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 28.571428298950195, 776.623369216919, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-51",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 158.441556930542, 776.623369216919, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-50",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 571.4285659790039, 816.40625, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "id": "obj-49",
                    "maxclass": "newobj",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 287.01298427581787, 876.6233682632446, 81.0, 22.0 ],
                    "text": "receive toport"
                }
            },
            {
                "box": {
                    "id": "obj-48",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 796.1038885116577, 390.9090871810913, 69.0, 22.0 ],
                    "text": "send toport"
                }
            },
            {
                "box": {
                    "bgcolor": [ 1.0, 0.7019607843137254, 0.23137254901960785, 1.0 ],
                    "format": 6,
                    "id": "obj-230",
                    "maxclass": "flonum",
                    "maximum": 15.0,
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 255.84415340423584, 88.31168746948242, 50.0, 22.0 ],
                    "textcolor": [ 0.0, 0.0, 0.0, 1.0 ]
                }
            },
            {
                "box": {
                    "bgcolor": [ 1.0, 1.0, 1.0, 1.0 ],
                    "color": [ 1.0, 0.725490196078431, 0.003921568627451, 1.0 ],
                    "id": "obj-24",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
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
                        "rect": [ 34.0, 95.0, 1444.0, 853.0 ],
                        "boxes": [
                            {
                                "box": {
                                    "comment": "",
                                    "id": "obj-2",
                                    "index": 1,
                                    "maxclass": "outlet",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "patching_rect": [ 46.0, 224.0, 30.0, 30.0 ]
                                }
                            },
                            {
                                "box": {
                                    "comment": "",
                                    "id": "obj-1",
                                    "index": 1,
                                    "maxclass": "inlet",
                                    "numinlets": 0,
                                    "numoutlets": 1,
                                    "outlettype": [ "" ],
                                    "patching_rect": [ 158.0, 88.0, 30.0, 30.0 ]
                                }
                            },
                            {
                                "box": {
                                    "id": "obj-233",
                                    "maxclass": "newobj",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 50.0, 187.0, 43.0, 22.0 ],
                                    "text": "cycle~"
                                }
                            },
                            {
                                "box": {
                                    "id": "obj-135",
                                    "maxclass": "newobj",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 50.0, 160.0, 46.0, 22.0 ],
                                    "text": "+~ 440"
                                }
                            },
                            {
                                "box": {
                                    "id": "obj-126",
                                    "maxclass": "newobj",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 50.0, 129.0, 29.5, 22.0 ],
                                    "text": "*~"
                                }
                            },
                            {
                                "box": {
                                    "id": "obj-125",
                                    "maxclass": "newobj",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [ "signal" ],
                                    "patching_rect": [ 50.0, 100.0, 53.0, 22.0 ],
                                    "text": "cycle~ 1"
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [ "obj-126", 1 ],
                                    "source": [ "obj-1", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [ "obj-126", 0 ],
                                    "source": [ "obj-125", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [ "obj-135", 0 ],
                                    "source": [ "obj-126", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [ "obj-233", 0 ],
                                    "source": [ "obj-135", 0 ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [ "obj-2", 0 ],
                                    "source": [ "obj-233", 0 ]
                                }
                            }
                        ],
                        "color": [ 1.0, 0.725490196078431, 0.003921568627451, 1.0 ],
                        "saved_attribute_attributes": {
                            "color": {
                                "expression": "themecolor.live_display_handle_one"
                            }
                        }
                    },
                    "patching_rect": [ 255.84415340423584, 116.88311576843262, 90.0, 22.0 ],
                    "saved_attribute_attributes": {
                        "color": {
                            "expression": "themecolor.live_display_handle_one"
                        }
                    },
                    "saved_newobj_attribute_attributes": {
                        "color": {
                            "expression": "themecolor.live_display_handle_one"
                        }
                    },
                    "saved_object_attributes": {
                        "color": [ 1.0, 0.725490196078431, 0.003921568627451, 1.0 ]
                    },
                    "text": "p",
                    "varname": "Input_Tester"
                }
            },
            {
                "box": {
                    "id": "obj-21",
                    "maxclass": "newobj",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 719.4805126190186, 432.4675283432007, 151.0, 22.0 ],
                    "text": "receive MIDI_Note_Played"
                }
            },
            {
                "box": {
                    "id": "obj-20",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 571.4285659790039, 662.3376560211182, 139.0, 22.0 ],
                    "text": "send MIDI_Note_Played"
                }
            },
            {
                "box": {
                    "activedialcolor": [ 1.0, 0.0, 0.0, 1.0 ],
                    "activefgdialcolor": [ 0.071196037102503, 0.071195997168178, 0.071196007384196, 1.0 ],
                    "activeneedlecolor": [ 1.0, 0.349019607843137, 0.372549019607843, 1.0 ],
                    "dialcolor": [ 0.071196037102503, 0.071195997168178, 0.071196007384196, 1.0 ],
                    "focusbordercolor": [ 0.071196037102503, 0.071195997168178, 0.071196007384196, 1.0 ],
                    "id": "obj-7",
                    "maxclass": "live.dial",
                    "needlecolor": [ 0.8, 0.8, 0.8, 1.0 ],
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "float" ],
                    "parameter_enable": 1,
                    "patching_rect": [ 111.81818103790283, 227.246750831604, 90.0, 48.0 ],
                    "saved_attribute_attributes": {
                        "activedialcolor": {
                            "expression": ""
                        },
                        "activefgdialcolor": {
                            "expression": "themecolor.live_control_fg_on"
                        },
                        "activeneedlecolor": {
                            "expression": "themecolor.live_record"
                        },
                        "dialcolor": {
                            "expression": "themecolor.live_lcd_bg"
                        },
                        "focusbordercolor": {
                            "expression": "themecolor.live_lcd_bg"
                        },
                        "needlecolor": {
                            "expression": "themecolor.live_arranger_grid_tiles"
                        },
                        "textcolor": {
                            "expression": "themecolor.live_dial_needle"
                        },
                        "valueof": {
                            "parameter_longname": "Input Level",
                            "parameter_mmax": 3.0,
                            "parameter_modmode": 4,
                            "parameter_shortname": "Input Level",
                            "parameter_steps": 18,
                            "parameter_type": 0,
                            "parameter_unitstyle": 0
                        }
                    },
                    "textcolor": [ 0.8, 0.8, 0.8, 1.0 ],
                    "varname": "Input"
                }
            },
            {
                "box": {
                    "id": "obj-261",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 45.45454502105713, 697.402590751648, 260.63829600811005, 33.0 ],
                    "text": "Magnitudes de cada ancho de banda:\nBajos, Medios y Altos "
                }
            },
            {
                "box": {
                    "id": "obj-259",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 259.7402572631836, 618.181812286377, 64.0, 22.0 ],
                    "text": "snapshot~"
                }
            },
            {
                "box": {
                    "id": "obj-258",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 144.1558427810669, 618.181812286377, 64.0, 22.0 ],
                    "text": "snapshot~"
                }
            },
            {
                "box": {
                    "id": "obj-257",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 28.571428298950195, 618.181812286377, 64.0, 22.0 ],
                    "text": "snapshot~"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-256",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 259.7402572631836, 651.9480457305908, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-254",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 142.85714149475098, 651.9480457305908, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-252",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 28.571428298950195, 651.9480457305908, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-250",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 259.7402572631836, 576.6233711242676, 112.0, 22.0 ],
                    "text": "average~ 4096 rms"
                }
            },
            {
                "box": {
                    "id": "obj-248",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 814.2857065200806, 132.46753120422363, 150.0, 33.0 ],
                    "text": "Tiempo de memoria de la muestra en ms"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-246",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 719.4805126190186, 497.4025926589966, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "data": {
                        "clips": [
                            {
                                "absolutepath": "Macintosh HD:/Users/angelbustillos/Downloads/C Major - 2 Octaves (Cello Play Along).mp3",
                                "filename": "C Major - 2 Octaves (Cello Play Along).mp3",
                                "filekind": "audiofile",
                                "id": "u803001615",
                                "loop": 1,
                                "content_state": {
                                    "loop": 1
                                }
                            }
                        ]
                    },
                    "id": "obj-235",
                    "maxclass": "playlist~",
                    "mode": "basic",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "signal", "signal", "signal", "", "dictionary" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 81.81818103790283, 107.79220676422119, 150.0, 30.0 ],
                    "quality": "basic",
                    "saved_attribute_attributes": {
                        "candicane2": {
                            "expression": ""
                        },
                        "candicane3": {
                            "expression": ""
                        },
                        "candicane4": {
                            "expression": ""
                        },
                        "candicane5": {
                            "expression": ""
                        },
                        "candicane6": {
                            "expression": ""
                        },
                        "candicane7": {
                            "expression": ""
                        },
                        "candicane8": {
                            "expression": ""
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-228",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 311.6883087158203, 89.61038875579834, 114.66667008399963, 20.0 ],
                    "text": "Amplitud de Vibrato"
                }
            },
            {
                "box": {
                    "id": "obj-214",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 142.85714149475098, 576.6233711242676, 112.0, 22.0 ],
                    "text": "average~ 4096 rms"
                }
            },
            {
                "box": {
                    "id": "obj-213",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 28.571428298950195, 576.6233711242676, 112.0, 22.0 ],
                    "text": "average~ 4096 rms"
                }
            },
            {
                "box": {
                    "id": "obj-200",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 439.0908933877945, 618.181812286377, 56.0, 22.0 ],
                    "text": "metro 50"
                }
            },
            {
                "box": {
                    "id": "obj-199",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 618.181812286377, 529.8701248168945, 171.0, 22.0 ],
                    "text": "prepend /audio/real_frequency"
                }
            },
            {
                "box": {
                    "id": "obj-198",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 635.0649290084839, 625.9740200042725, 177.0, 22.0 ],
                    "text": "prepend /audio/base_frequency"
                }
            },
            {
                "box": {
                    "id": "obj-197",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 571.4285659790039, 757.1428499221802, 183.0, 22.0 ],
                    "text": "prepend /audio/vibrato_dif_cents"
                }
            },
            {
                "box": {
                    "bgcolor": [ 1.0, 0.725490196078431, 0.003921568627451, 1.0 ],
                    "id": "obj-193",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 258.4415559768677, 63.63636302947998, 88.0, 20.0 ],
                    "saved_attribute_attributes": {
                        "bgcolor": {
                            "expression": "themecolor.live_display_line_one"
                        }
                    },
                    "text": "Tester de Input",
                    "textcolor": [ 0.0, 0.0, 0.0, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-114",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 58.44155788421631, 253.246750831604, 29.5, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "obj-195",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 287.01298427581787, 909.0909004211426, 138.0, 22.0 ],
                    "text": "udpsend 127.0.0.1 8400"
                }
            },
            {
                "box": {
                    "id": "obj-194",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 796.1038885116577, 357.14285373687744, 184.0, 22.0 ],
                    "text": "prepend /audio/vibrato_depth_hz"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-189",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 796.1038885116577, 325.9740228652954, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-187",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 796.1038885116577, 294.8051919937134, 33.0, 22.0 ],
                    "text": "* 0.5"
                }
            },
            {
                "box": {
                    "id": "obj-186",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 751.9480447769165, 364.93506145477295, 29.5, 22.0 ],
                    "text": "-"
                }
            },
            {
                "box": {
                    "id": "obj-185",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 745.4545383453369, 210.3896083831787, 43.0, 22.0 ],
                    "text": "zlclear"
                }
            },
            {
                "box": {
                    "id": "obj-182",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "bang" ],
                    "patching_rect": [ 771.4285640716553, 175.32467365264893, 32.0, 22.0 ],
                    "text": "t b b"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-181",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 723.3766164779663, 325.9740228652954, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-179",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 723.3766164779663, 294.8051919937134, 57.0, 22.0 ],
                    "text": "minimum"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-178",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 654.5454483032227, 325.9740228652954, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-176",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 654.5454483032227, 294.8051919937134, 61.0, 22.0 ],
                    "text": "maximum"
                }
            },
            {
                "box": {
                    "id": "obj-174",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 620.7792148590088, 210.3896083831787, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-170",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 620.7792148590088, 371.42856788635254, 118.0, 22.0 ],
                    "text": "print vibrato_window"
                }
            },
            {
                "box": {
                    "id": "obj-167",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 740.2597332000732, 107.79220676422119, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-161",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 654.5454483032227, 259.7402572631836, 75.0, 22.0 ],
                    "text": "zl group 256"
                }
            },
            {
                "box": {
                    "id": "obj-145",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 740.2597332000732, 144.1558427810669, 63.0, 22.0 ],
                    "text": "metro 256"
                }
            },
            {
                "box": {
                    "id": "obj-134",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 284.41558170318604, 941.5584325790405, 150.0, 20.0 ],
                    "text": "@period 128 @size 2048"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-117",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 654.5454483032227, 210.3896083831787, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "bgcolor": [ 0.9, 0.65, 0.05, 1.0 ],
                    "id": "obj-113",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 623.3766174316406, 728.57142162323, 123.40425789356232, 20.0 ],
                    "saved_attribute_attributes": {
                        "bgcolor": {
                            "expression": "themecolor.live_control_selection"
                        },
                        "textcolor": {
                            "expression": "themecolor.live_meter_bg"
                        }
                    },
                    "text": "Δ de vibrato en cents",
                    "textcolor": [ 0.071196037102503, 0.071195997168178, 0.071196007384196, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-94",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 642.8571367263794, 583.1168775558472, 133.6206966638565, 33.0 ],
                    "text": "para que cuando haya silencio marque 0"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-75",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 571.4285659790039, 727.2727203369141, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-71",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 571.4285659790039, 697.402590751648, 343.0, 22.0 ],
                    "text": "expr ($f1 > 0.) * (1200. * log(max($f1\\, 0.000001) / $f2) / log(2.))"
                }
            },
            {
                "box": {
                    "id": "obj-68",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 719.4805126190186, 463.6363592147827, 32.0, 22.0 ],
                    "text": "mtof"
                }
            },
            {
                "box": {
                    "bgcolor": [ 0.0, 0.933333333333333, 1.0, 1.0 ],
                    "id": "obj-67",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 771.4285640716553, 497.4025926589966, 132.85714602470398, 20.0 ],
                    "saved_attribute_attributes": {
                        "bgcolor": {
                            "expression": "themecolor.live_display_line_two"
                        }
                    },
                    "text": "Frecuencia Temperada",
                    "textcolor": [ 0.0, 0.0, 0.0, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-65",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "int", "int" ],
                    "patching_rect": [ 570.129864692688, 593.5064878463745, 71.0, 22.0 ],
                    "text": "maximum 0"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-64",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 571.4285659790039, 624.6753187179565, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-53",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 570.129864692688, 529.8701248168945, 32.0, 22.0 ],
                    "text": "ftom"
                }
            },
            {
                "box": {
                    "id": "obj-42",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 570.129864692688, 562.3376569747925, 39.0, 22.0 ],
                    "text": "round"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-40",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 198.70129680633545, 325.9740228652954, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-35",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "float", "float", "" ],
                    "patching_rect": [ 280.5194778442383, 967.5324583053589, 210.0, 22.0 ],
                    "text": "fzero~ @freqmin 20 @freqmax 15000"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-34",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 198.70129680633545, 394.80519104003906, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-32",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 198.70129680633545, 368.8311653137207, 82.0, 22.0 ],
                    "text": "peakamp~ 20"
                }
            },
            {
                "box": {
                    "id": "obj-31",
                    "maxclass": "meter~",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 198.70129680633545, 285.71428298950195, 179.3103542327881, 30.827566266059875 ]
                }
            },
            {
                "box": {
                    "id": "obj-26",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 215.58441352844238, 262.33765983581543, 98.03672808408737, 20.0 ],
                    "text": "/audio/amplitude"
                }
            },
            {
                "box": {
                    "bgcolor": [ 0.745098, 0.596078, 1.0, 1.0 ],
                    "id": "obj-25",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 618.181812286377, 483.1168785095215, 98.03672808408737, 20.0 ],
                    "saved_attribute_attributes": {
                        "bgcolor": {
                            "expression": "themecolor.live_scale_awareness"
                        }
                    },
                    "text": "Frecuencia Real",
                    "textcolor": [ 0.0, 0.0, 0.0, 1.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-4",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 570.129864692688, 481.81817722320557, 50.0, 22.0 ]
                }
            },
            {
                "box": {
                    "domain": [ 0.0, 6000.0 ],
                    "fgcolor": [ 0.9568627450980393, 1.0, 0.0, 1.0 ],
                    "id": "obj-249",
                    "maxclass": "spectroscope~",
                    "monochrome": 0,
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 58.44155788421631, 398.7012948989868, 115.0, 45.0 ]
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "grad1": [ 0.043137254901960784, 0.011764705882352941, 0.10980392156862745, 1.0 ],
                    "grad2": [ 0.25882352941176473, 0.18823529411764706, 0.18823529411764706, 1.0 ],
                    "id": "obj-19",
                    "maxclass": "panel",
                    "mode": 1,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 506.824670791626, 102.98707586526871, 529.8701248168945, 719.9219435453415 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "grad1": [ 0.00784313725490196, 0.0196078431372549, 0.01568627450980392, 1.0 ],
                    "grad2": [ 0.158640689195807, 0.158640642399981, 0.158640654628478, 1.0 ],
                    "id": "obj-45",
                    "maxclass": "panel",
                    "mode": 1,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1041.5584316253662, 102.59740161895752, 307.79220485687256, 538.961033821106 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "fontface": 2,
                    "fontname": "Arial Black",
                    "fontsize": 36.0,
                    "id": "obj-43",
                    "maxclass": "comment",
                    "numinlets": 0,
                    "numoutlets": 0,
                    "patching_rect": [ 27.272727012634277, 15.584415435791016, 129.8701286315918, 57.0 ],
                    "style": "rnbodefault",
                    "suppressinlet": 1,
                    "text": "Input",
                    "textcolor": [ 1.0, 1.0, 1.0, 1.0 ]
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "bgcolor": [ 0.0, 0.0, 0.0, 1.0 ],
                    "id": "obj-23",
                    "maxclass": "panel",
                    "mode": 0,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 10.389610290527344, 7.792207717895508, 492.076906979084, 196.0000058412552 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "bgcolor": [ 0.0, 0.0, 0.0, 1.0 ],
                    "id": "obj-63",
                    "maxclass": "panel",
                    "mode": 0,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 11.688311576843262, 825.9740180969238, 492.076906979084, 196.0000058412552 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "grad1": [ 0.00784313725490196, 0.0196078431372549, 0.01568627450980392, 1.0 ],
                    "grad2": [ 0.158640689195807, 0.158640642399981, 0.158640654628478, 1.0 ],
                    "id": "obj-87",
                    "maxclass": "panel",
                    "mode": 1,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1042.0289942026138, 648.5507300496101, 307.24637937545776, 255.07246589660645 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "background": 1,
                    "grad1": [ 0.6470588235294118, 0.18823529411764706, 0.27058823529411763, 1.0 ],
                    "grad2": [ 0.054901960784313725, 0.047058823529411764, 0.047058823529411764, 1.0 ],
                    "id": "obj-17",
                    "maxclass": "panel",
                    "mode": 1,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 11.688311576843262, 520.7792158126831, 491.0257030725479, 300.0000379085541 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "background": 1,
                    "grad1": [ 0.42745098039215684, 0.25098039215686274, 0.25098039215686274, 1.0 ],
                    "grad2": [ 0.0196078431372549, 0.01568627450980392, 0.01568627450980392, 1.0 ],
                    "id": "obj-8",
                    "maxclass": "panel",
                    "mode": 1,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 9.090909004211426, 206.49350452423096, 493.5898059606552, 306.4102951288223 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "id": "obj-fx-title",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1560.0, 60.0, 720.0, 20.0 ],
                    "text": "EFFECTS BY HAND SIGNS -> ABLETON / TD  (cello app -> udpreceive 7400: /fx/pingpong, /fx/overdrive, /fx/delay, /fx/coordinateschange  1|0)"
                }
            },
            {
                "box": {
                    "id": "obj-fx-help",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1560.0, 82.0, 1200.0, 20.0 ],
                    "text": "-> MIDI CC on 'From Max 1', channel 1, sent only when it changes: ping-pong CC 20, overdrive CC 21, delay CC 22 (Live), coordinates change CC 23 (TouchDesigner) (127 on, 0 off; all can be on). In Live: Remote on for 'from Max 1', then MIDI Map each effect's on/off."
                }
            },
            {
                "box": {
                    "id": "obj-fx-udp",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1560.0, 120.0, 126.5, 22.0 ],
                    "text": "udpreceive 7400"
                }
            },
            {
                "box": {
                    "id": "obj-fx-route",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 5,
                    "outlettype": [ "", "", "", "", "" ],
                    "patching_rect": [ 1560.0, 155.0, 420.0, 22.0 ],
                    "text": "route /fx/overdrive /fx/pingpong /fx/delay /fx/coordinateschange"
                }
            },
            {
                "box": {
                    "id": "obj-fx-odl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1560.0, 190.0, 80.0, 20.0 ],
                    "text": "overdrive"
                }
            },
            {
                "box": {
                    "id": "obj-fx-odt",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1560.0, 212.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-fx-ppl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1720.0, 190.0, 80.0, 20.0 ],
                    "text": "ping-pong"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ppt",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1720.0, 212.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-dsp-lb",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 1920.0, 120.0, 60.0, 22.0 ],
                    "text": "loadbang"
                }
            },
            {
                "box": {
                    "id": "obj-dsp-del",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 1920.0, 155.0, 70.0, 22.0 ],
                    "text": "delay 500"
                }
            },
            {
                "box": {
                    "id": "obj-dsp-msg",
                    "linecount": 2,
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1920.0, 190.0, 55.0, 35.0 ],
                    "text": ";\rdsp start"
                }
            },
            {
                "box": {
                    "id": "obj-dsp-c",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 2010.0, 190.0, 230.0, 20.0 ],
                    "text": "audio on when the patch opens"
                }
            },
            {
                "box": {
                    "id": "obj-fx-odcc127",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1560.0, 275.0, 45.0, 22.0 ],
                    "text": "* 127"
                }
            },
            {
                "box": {
                    "id": "obj-fx-odccout",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 0,
                    "patching_rect": [ 1560.0, 310.0, 140.0, 22.0 ],
                    "text": "ctlout \"From Max 1\" 21 1"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ppcc127",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1720.0, 275.0, 45.0, 22.0 ],
                    "text": "* 127"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ppccout",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 0,
                    "patching_rect": [ 1720.0, 310.0, 140.0, 22.0 ],
                    "text": "ctlout \"From Max 1\" 20 1"
                }
            },
            {
                "box": {
                    "id": "obj-fx-dll",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1880.0, 190.0, 80.0, 20.0 ],
                    "text": "delay"
                }
            },
            {
                "box": {
                    "id": "obj-fx-dlt",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1880.0, 212.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-fx-dlcc127",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1880.0, 275.0, 45.0, 22.0 ],
                    "text": "* 127"
                }
            },
            {
                "box": {
                    "id": "obj-fx-dlccout",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 0,
                    "patching_rect": [ 1880.0, 310.0, 140.0, 22.0 ],
                    "text": "ctlout \"From Max 1\" 22 1"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ccl",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 2040.0, 190.0, 130.0, 20.0 ],
                    "text": "coordinates change"
                }
            },
            {
                "box": {
                    "id": "obj-fx-cct",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 2040.0, 212.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-fx-cccc127",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 2040.0, 275.0, 45.0, 22.0 ],
                    "text": "* 127"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ccccout",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 0,
                    "patching_rect": [ 2040.0, 310.0, 140.0, 22.0 ],
                    "text": "ctlout \"From Max 1\" 23 1"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ccchange",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 2040.0, 245.0, 50.0, 22.0 ],
                    "text": "change"
                }
            },
            {
                "box": {
                    "id": "obj-fx-ppchange",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 1720.0, 245.0, 50.0, 22.0 ],
                    "text": "change"
                }
            },
            {
                "box": {
                    "id": "obj-fx-odchange",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 1560.0, 245.0, 50.0, 22.0 ],
                    "text": "change"
                }
            },
            {
                "box": {
                    "id": "obj-fx-dlchange",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "int", "int" ],
                    "patching_rect": [ 1880.0, 245.0, 50.0, 22.0 ],
                    "text": "change"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-101", 0 ],
                    "source": [ "obj-100", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-103", 0 ],
                    "source": [ "obj-101", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-105", 0 ],
                    "source": [ "obj-103", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-104", 0 ],
                    "source": [ "obj-105", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-111", 0 ],
                    "midpoints": [ 401.3181678056717, 607.5816758652218, 462.0, 607.5816758652218, 462.0, 579.0, 476.0194778442383, 579.0 ],
                    "source": [ "obj-109", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-200", 0 ],
                    "source": [ "obj-111", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-249", 0 ],
                    "midpoints": [ 67.94155788421631, 276.80798065662384, 67.94155788421631, 276.80798065662384 ],
                    "order": 2,
                    "source": [ "obj-114", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-31", 0 ],
                    "midpoints": [ 67.94155788421631, 288.47279953956604, 208.20129680633545, 288.47279953956604 ],
                    "order": 1,
                    "source": [ "obj-114", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-32", 0 ],
                    "midpoints": [ 67.94155788421631, 366.1209171153605, 208.20129680633545, 366.1209171153605 ],
                    "order": 0,
                    "source": [ "obj-114", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-5", 0 ],
                    "midpoints": [ 67.94155788421631, 350.2594148693606, 36.77272701263428, 350.2594148693606 ],
                    "order": 3,
                    "source": [ "obj-114", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-167", 0 ],
                    "source": [ "obj-115", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-161", 0 ],
                    "source": [ "obj-117", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-41", 0 ],
                    "source": [ "obj-14", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-161", 0 ],
                    "midpoints": [ 749.7597332000732, 189.61202711751685, 715.2597408294678, 189.61202711751685, 715.2597408294678, 243.80798065662384, 664.0454483032227, 243.80798065662384 ],
                    "order": 1,
                    "source": [ "obj-145", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-182", 0 ],
                    "order": 0,
                    "source": [ "obj-145", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-82", 0 ],
                    "source": [ "obj-16", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-176", 0 ],
                    "midpoints": [ 664.0454483032227, 298.46396361052985, 664.0454483032227, 298.46396361052985 ],
                    "order": 1,
                    "source": [ "obj-161", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-179", 0 ],
                    "midpoints": [ 664.0454483032227, 289.8175987540185, 732.8766164779663, 289.8175987540185 ],
                    "order": 0,
                    "source": [ "obj-161", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-145", 0 ],
                    "source": [ "obj-167", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-161", 0 ],
                    "source": [ "obj-174", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-178", 0 ],
                    "source": [ "obj-176", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-186", 0 ],
                    "midpoints": [ 664.0454483032227, 360.1770828342437, 761.4480447769165, 360.1770828342437 ],
                    "source": [ "obj-178", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-181", 0 ],
                    "source": [ "obj-179", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-186", 1 ],
                    "midpoints": [ 732.8766164779663, 355.13087548775593, 771.9480447769165, 355.13087548775593 ],
                    "source": [ "obj-181", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.0, 0.42460423707962036, 0.0, 1.0 ],
                    "destination": [ "obj-161", 0 ],
                    "midpoints": [ 793.9285640716553, 251.744682236053, 664.0454483032227, 251.744682236053 ],
                    "source": [ "obj-182", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-185", 0 ],
                    "source": [ "obj-182", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.883908748626709, 0.2662561535835266, 0.21121874451637268, 1.0 ],
                    "destination": [ "obj-161", 1 ],
                    "source": [ "obj-185", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-187", 0 ],
                    "midpoints": [ 761.4480447769165, 390.1770828342437, 792.2575237226487, 390.1770828342437, 792.2575237226487, 291.1770828342437, 805.6038885116577, 291.1770828342437 ],
                    "source": [ "obj-186", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-189", 0 ],
                    "source": [ "obj-187", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-194", 0 ],
                    "source": [ "obj-189", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-48", 0 ],
                    "source": [ "obj-194", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-50", 0 ],
                    "source": [ "obj-197", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-257", 1 ],
                    "order": 2,
                    "source": [ "obj-200", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-258", 1 ],
                    "order": 1,
                    "source": [ "obj-200", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-259", 1 ],
                    "order": 0,
                    "source": [ "obj-200", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-68", 0 ],
                    "midpoints": [ 728.9805126190186, 460.70041954517365, 728.9805126190186, 460.70041954517365 ],
                    "source": [ "obj-21", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-257", 0 ],
                    "source": [ "obj-213", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-258", 0 ],
                    "source": [ "obj-214", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-24", 0 ],
                    "source": [ "obj-230", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-30", 0 ],
                    "source": [ "obj-235", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.194305419921875, 0.9678335785865784, 0.9904032349586487, 1.0 ],
                    "destination": [ "obj-71", 1 ],
                    "midpoints": [ 728.9805126190186, 526.2278087735176, 821.7121245265007, 526.2278087735176, 821.7121245265007, 691.2278087735176, 904.9285659790039, 691.2278087735176 ],
                    "source": [ "obj-246", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-259", 0 ],
                    "source": [ "obj-250", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-54", 0 ],
                    "source": [ "obj-252", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-55", 0 ],
                    "source": [ "obj-254", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-56", 0 ],
                    "source": [ "obj-256", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-252", 0 ],
                    "source": [ "obj-257", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-254", 0 ],
                    "source": [ "obj-258", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-256", 0 ],
                    "source": [ "obj-259", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-77", 0 ],
                    "source": [ "obj-27", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-73", 1 ],
                    "source": [ "obj-28", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-73", 0 ],
                    "source": [ "obj-28", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-2", 0 ],
                    "source": [ "obj-3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-114", 0 ],
                    "order": 1,
                    "source": [ "obj-30", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "midpoints": [ 235.47402381896973, 186.80798065662384, 496.2597408294678, 186.80798065662384, 496.2597408294678, 95.29905198514462, 1064.0454444885254, 95.29905198514462 ],
                    "order": 0,
                    "source": [ "obj-30", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-40", 0 ],
                    "order": 1,
                    "source": [ "obj-31", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-99", 0 ],
                    "order": 0,
                    "source": [ "obj-31", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-34", 0 ],
                    "source": [ "obj-32", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-72", 0 ],
                    "source": [ "obj-33", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-39", 0 ],
                    "source": [ "obj-38", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-74", 0 ],
                    "source": [ "obj-39", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-199", 0 ],
                    "order": 0,
                    "source": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-53", 0 ],
                    "order": 2,
                    "source": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.4490174651145935, 0.19766229391098022, 0.5546131134033203, 1.0 ],
                    "destination": [ "obj-71", 0 ],
                    "midpoints": [ 579.629864692688, 520.2278087735176, 557.7121245265007, 520.2278087735176, 557.7121245265007, 691.2278087735176, 580.9285659790039, 691.2278087735176 ],
                    "order": 1,
                    "source": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-3", 0 ],
                    "midpoints": [ 208.20129680633545, 348.80798065662384, 184.25974082946777, 348.80798065662384, 184.25974082946777, 435.80798065662384, 208.20129680633545, 435.80798065662384 ],
                    "source": [ "obj-40", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-44", 0 ],
                    "source": [ "obj-41", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-65", 0 ],
                    "source": [ "obj-42", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-85", 0 ],
                    "source": [ "obj-47", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-195", 0 ],
                    "source": [ "obj-49", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-58", 0 ],
                    "source": [ "obj-5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-42", 0 ],
                    "source": [ "obj-53", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-52", 0 ],
                    "source": [ "obj-54", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-51", 0 ],
                    "source": [ "obj-55", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-57", 0 ],
                    "source": [ "obj-56", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-213", 0 ],
                    "source": [ "obj-58", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-61", 0 ],
                    "source": [ "obj-58", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-81", 0 ],
                    "source": [ "obj-6", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-214", 0 ],
                    "source": [ "obj-61", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-250", 0 ],
                    "source": [ "obj-61", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-198", 0 ],
                    "midpoints": [ 580.9285659790039, 652.6557411805261, 630.1258755326271, 652.6557411805261, 630.1258755326271, 621.5927998423576, 644.5649290084839, 621.5927998423576 ],
                    "order": 0,
                    "source": [ "obj-64", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-20", 0 ],
                    "order": 1,
                    "source": [ "obj-64", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-64", 0 ],
                    "source": [ "obj-65", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-38", 0 ],
                    "source": [ "obj-66", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.0, 0.9717233777046204, 0.9694718718528748, 1.0 ],
                    "destination": [ "obj-246", 0 ],
                    "midpoints": [ 728.9805126190186, 489.0663514446933, 728.9805126190186, 489.0663514446933 ],
                    "source": [ "obj-68", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-66", 0 ],
                    "source": [ "obj-69", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-114", 1 ],
                    "source": [ "obj-7", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 0 ],
                    "source": [ "obj-70", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-75", 0 ],
                    "source": [ "obj-71", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 1 ],
                    "source": [ "obj-72", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-28", 0 ],
                    "source": [ "obj-74", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-197", 0 ],
                    "source": [ "obj-75", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-74", 0 ],
                    "midpoints": [ 1271.948040008545, 364.92207622528076, 1133.797901749611, 364.92207622528076, 1133.797901749611, 424.92207622528076, 1095.2142753601074, 424.92207622528076 ],
                    "source": [ "obj-76", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-80", 0 ],
                    "midpoints": [ 1261.448040008545, 354.05098247528076, 1187.4220666885376, 354.05098247528076 ],
                    "source": [ "obj-76", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-33", 0 ],
                    "source": [ "obj-77", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-70", 0 ],
                    "source": [ "obj-78", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-78", 0 ],
                    "source": [ "obj-79", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-27", 0 ],
                    "source": [ "obj-80", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-79", 0 ],
                    "source": [ "obj-80", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-16", 0 ],
                    "source": [ "obj-81", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.49770504236221313, 0.2039368748664856, 0.7070547342300415, 1.0 ],
                    "destination": [ "obj-117", 0 ],
                    "midpoints": [ 999.4224959611893, 264.80798065662384, 742.2597408294678, 264.80798065662384, 742.2597408294678, 243.80798065662384, 722.4823970794678, 243.80798065662384, 722.4823970794678, 195.80798065662384, 664.0454483032227, 195.80798065662384 ],
                    "order": 0,
                    "source": [ "obj-82", 0 ]
                }
            },
            {
                "patchline": {
                    "color": [ 0.4980633854866028, 0.20399847626686096, 0.7058204412460327, 1.0 ],
                    "destination": [ "obj-4", 0 ],
                    "midpoints": [ 999.4224959611893, 423.86613942310214, 579.629864692688, 423.86613942310214 ],
                    "order": 1,
                    "source": [ "obj-82", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-69", 0 ],
                    "source": [ "obj-82", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-76", 0 ],
                    "order": 1,
                    "source": [ "obj-82", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-93", 0 ],
                    "order": 0,
                    "source": [ "obj-82", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-30", 0 ],
                    "order": 0,
                    "source": [ "obj-84", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-86", 0 ],
                    "order": 1,
                    "source": [ "obj-84", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-44", 0 ],
                    "source": [ "obj-85", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-91", 0 ],
                    "order": 0,
                    "source": [ "obj-93", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-96", 0 ],
                    "order": 1,
                    "source": [ "obj-93", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-95", 0 ],
                    "source": [ "obj-96", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-100", 0 ],
                    "source": [ "obj-99", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-dsp-msg", 0 ],
                    "source": [ "obj-dsp-del", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-dsp-del", 0 ],
                    "source": [ "obj-dsp-lb", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-odccout", 0 ],
                    "source": [ "obj-fx-odcc127", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-ppccout", 0 ],
                    "source": [ "obj-fx-ppcc127", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-odt", 0 ],
                    "source": [ "obj-fx-route", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-ppt", 0 ],
                    "source": [ "obj-fx-route", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-route", 0 ],
                    "source": [ "obj-fx-udp", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-dlt", 0 ],
                    "source": [ "obj-fx-route", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-dlccout", 0 ],
                    "source": [ "obj-fx-dlcc127", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-cct", 0 ],
                    "source": [ "obj-fx-route", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-fx-ccccout", 0 ],
                    "source": [ "obj-fx-cccc127", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-cct", 0 ],
                    "destination": [ "obj-fx-ccchange", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-ccchange", 0 ],
                    "destination": [ "obj-fx-cccc127", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-ppt", 0 ],
                    "destination": [ "obj-fx-ppchange", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-ppchange", 0 ],
                    "destination": [ "obj-fx-ppcc127", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-odt", 0 ],
                    "destination": [ "obj-fx-odchange", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-odchange", 0 ],
                    "destination": [ "obj-fx-odcc127", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-dlt", 0 ],
                    "destination": [ "obj-fx-dlchange", 0 ]
                }
            },
            {
                "patchline": {
                    "source": [ "obj-fx-dlchange", 0 ],
                    "destination": [ "obj-fx-dlcc127", 0 ]
                }
            }
        ],
        "parameters": {
            "obj-14": [ "IR_Contrast", "IR_Contrast", 0 ],
            "obj-47": [ "IR_Brightness", "IR_Brightness", 0 ],
            "obj-7": [ "Input Level", "Input Level", 0 ],
            "obj-97::obj-20": [ "letterbox_menu", "letterbox_menu", 0 ],
            "obj-97::obj-37": [ "aspect_menu", "aspect_menu", 0 ],
            "parameterbanks": {
                "0": {
                    "index": 0,
                    "name": "",
                    "parameters": [ "-", "-", "-", "-", "-", "-", "-", "-" ],
                    "buttons": [ "-", "-", "-", "-", "-", "-", "-", "-" ]
                }
            },
            "inherited_shortname": 1
        },
        "autosave": 0,
        "styles": [
            {
                "name": "rnbodefault",
                "default": {
                    "accentcolor": [ 0.343034118413925, 0.506230533123016, 0.86220508813858, 1.0 ],
                    "bgcolor": [ 0.031372549019608, 0.125490196078431, 0.211764705882353, 1.0 ],
                    "bgfillcolor": {
                        "angle": 270.0,
                        "autogradient": 0.0,
                        "color": [ 0.031372549019608, 0.125490196078431, 0.211764705882353, 1.0 ],
                        "color1": [ 0.031372549019608, 0.125490196078431, 0.211764705882353, 1.0 ],
                        "color2": [ 0.263682, 0.004541, 0.038797, 1.0 ],
                        "proportion": 0.39,
                        "type": "color"
                    },
                    "color": [ 0.929412, 0.929412, 0.352941, 1.0 ],
                    "elementcolor": [ 0.357540726661682, 0.515565991401672, 0.861786782741547, 1.0 ],
                    "fontname": [ "Lato" ],
                    "fontsize": [ 12.0 ],
                    "stripecolor": [ 0.258338063955307, 0.352425158023834, 0.511919498443604, 1.0 ],
                    "textcolor_inverse": [ 0.968627, 0.968627, 0.968627, 1 ]
                },
                "parentstyle": "",
                "multi": 0
            },
            {
                "name": "rnbolight",
                "default": {
                    "accentcolor": [ 0.443137254901961, 0.505882352941176, 0.556862745098039, 1.0 ],
                    "bgcolor": [ 0.796078431372549, 0.862745098039216, 0.925490196078431, 1.0 ],
                    "bgfillcolor": {
                        "angle": 270.0,
                        "autogradient": 0.0,
                        "color": [ 0.835294117647059, 0.901960784313726, 0.964705882352941, 1.0 ],
                        "color1": [ 0.031372549019608, 0.125490196078431, 0.211764705882353, 1.0 ],
                        "color2": [ 0.263682, 0.004541, 0.038797, 1.0 ],
                        "proportion": 0.39,
                        "type": "color"
                    },
                    "clearcolor": [ 0.898039, 0.898039, 0.898039, 1.0 ],
                    "color": [ 0.815686274509804, 0.509803921568627, 0.262745098039216, 1.0 ],
                    "editing_bgcolor": [ 0.898039, 0.898039, 0.898039, 1.0 ],
                    "elementcolor": [ 0.337254901960784, 0.384313725490196, 0.462745098039216, 1.0 ],
                    "fontname": [ "Lato" ],
                    "locked_bgcolor": [ 0.898039, 0.898039, 0.898039, 1.0 ],
                    "stripecolor": [ 0.309803921568627, 0.698039215686274, 0.764705882352941, 1.0 ],
                    "textcolor_inverse": [ 0.0, 0.0, 0.0, 1.0 ]
                },
                "parentstyle": "",
                "multi": 0
            }
        ],
        "editing_bgcolor": [ 0.12941176470588237, 0.12941176470588237, 0.12941176470588237, 1.0 ]
    }
}