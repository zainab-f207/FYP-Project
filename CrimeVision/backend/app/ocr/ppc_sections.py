"""
Comprehensive Pakistan Penal Code (PPC) Sections Mapping
Act XLV of 1860 - All sections mapped to English crime/offence names.

This module provides:
1. PPC_SECTIONS: Dict mapping section number (str) -> English description
2. get_crime_name(section): Returns English name for a PPC section
3. get_crime_names(sections_list): Returns list of (section, crime_name) tuples
"""

# Complete PPC Sections Dictionary
# Section numbers as strings to handle sub-sections like "302", "337-A", "489-F" etc.
PPC_SECTIONS = {
    # ==========================================
    # CHAPTER I - INTRODUCTION (Sections 1-5)
    # ==========================================
    "1": "Title and Extent of Operation of the Code",
    "2": "Punishment of Offences Committed Within Pakistan",
    "3": "Punishment of Offences Committed Beyond Pakistan",
    "4": "Extension of Code to Extra-Territorial Offences",
    "5": "Certain Laws Not Affected by This Act",

    # ==========================================
    # CHAPTER II - GENERAL EXPLANATIONS (Sections 6-52A)
    # ==========================================
    "6": "Definitions Subject to Exceptions",
    "7": "Sense of Expression Once Explained",
    "8": "Gender",
    "9": "Number",
    "10": "Definition of Man and Woman",
    "11": "Definition of Person",
    "12": "Definition of Public",
    "14": "Definition of Servant of the State",
    "17": "Definition of Government",
    "19": "Definition of Judge",
    "20": "Definition of Court of Justice",
    "21": "Definition of Public Servant",
    "22": "Definition of Movable Property",
    "23": "Wrongful Gain and Wrongful Loss",
    "24": "Definition of Dishonestly",
    "25": "Definition of Fraudulently",
    "26": "Reason to Believe",
    "27": "Property in Possession of Wife, Clerk or Servant",
    "28": "Definition of Counterfeit",
    "29": "Definition of Document",
    "30": "Definition of Valuable Security",
    "31": "Definition of A Will",
    "32": "Words Referring to Acts Include Illegal Omissions",
    "33": "Definition of Act and Omission",
    "34": "Acts Done by Several Persons in Furtherance of Common Intention",
    "35": "Criminal Act Done with Criminal Knowledge or Intention",
    "36": "Effect Caused Partly by Act and Partly by Omission",
    "37": "Co-operation by Doing One of Several Acts Constituting an Offence",
    "38": "Persons Concerned in Criminal Act May Be Guilty of Different Offences",
    "39": "Definition of Voluntarily",
    "40": "Definition of Offence",
    "41": "Definition of Special Law",
    "42": "Definition of Local Law",
    "43": "Definition of Illegal",
    "44": "Definition of Injury",
    "45": "Definition of Life",
    "46": "Definition of Death",
    "47": "Definition of Animal",
    "48": "Definition of Vessel",
    "49": "Definition of Year and Month",
    "50": "Definition of Section",
    "51": "Definition of Oath",
    "52": "Definition of Good Faith",
    "52-A": "Definition of Harbour",

    # ==========================================
    # CHAPTER III - OF PUNISHMENTS (Sections 53-75)
    # ==========================================
    "53": "Types of Punishments (Qisas, Diyat, Arsh, Daman, Tazir, Imprisonment, Fine)",
    "54": "Commutation of Sentence of Death",
    "55": "Commutation of Sentence of Imprisonment for Life",
    "55-A": "Saving for President's Prerogative",
    "57": "Fractions of Terms of Punishment",
    "60": "Sentence May Be Rigorous or Simple",
    "63": "Amount of Fine",
    "64": "Sentence of Imprisonment for Non-Payment of Fine",
    "65": "Limit to Imprisonment for Non-Payment of Fine",
    "66": "Description of Imprisonment for Non-Payment of Fine",
    "67": "Imprisonment for Non-Payment of Fine (Fine Only Offence)",
    "68": "Imprisonment to Terminate on Payment of Fine",
    "69": "Termination of Imprisonment on Payment of Proportional Part of Fine",
    "70": "Fine Leviable Within Six Years",
    "71": "Limit of Punishment of Offence Made Up of Several Offences",
    "72": "Punishment When Doubtful of Which Offence Guilty",
    "73": "Solitary Confinement",
    "74": "Limit of Solitary Confinement",
    "75": "Enhanced Punishment After Previous Conviction",

    # ==========================================
    # CHAPTER IV - GENERAL EXCEPTIONS (Sections 76-106)
    # ==========================================
    "76": "Act Done by Person Bound by Law (Mistake of Fact)",
    "77": "Act of Judge When Acting Judicially",
    "78": "Act Done Pursuant to Judgment or Order of Court",
    "79": "Act Done by Person Justified by Law",
    "80": "Accident in Doing a Lawful Act",
    "81": "Act Likely to Cause Harm Done Without Criminal Intent",
    "82": "Act of Child Under Seven Years (Not an Offence)",
    "83": "Act of Child Between 7-12 of Immature Understanding",
    "84": "Act of a Person of Unsound Mind",
    "85": "Act of Person Intoxicated Against His Will",
    "86": "Offence Requiring Knowledge - Intoxicated Person",
    "87": "Act Not Intended and Not Known to Cause Death (Consent)",
    "88": "Act Not Intended to Cause Death Done by Consent in Good Faith",
    "89": "Act Done in Good Faith for Benefit of Child or Insane Person",
    "90": "Consent Known to Be Given Under Fear or Misconception",
    "91": "Exclusion of Acts Which Are Offences Independently of Harm",
    "92": "Act Done in Good Faith for Benefit of Person Without Consent",
    "93": "Communication Made in Good Faith",
    "94": "Act to Which Person is Compelled by Threats (Duress)",
    "95": "Act Causing Slight Harm",
    "96": "Right of Private Defence",
    "97": "Right of Private Defence of Body and Property",
    "98": "Right of Private Defence Against Person of Unsound Mind",
    "99": "Acts Against Which There Is No Right of Private Defence",
    "100": "Right of Private Defence of Body Extending to Causing Death",
    "101": "When Right of Private Defence of Body Extends to Causing Death",
    "102": "Commencement and Continuance of Right of Private Defence of Body",
    "103": "Right of Private Defence of Property Extending to Causing Death",
    "104": "When Right Extends to Causing Death (Property)",
    "105": "Commencement and Continuance of Right of Private Defence of Property",
    "106": "Right of Private Defence Against Deadly Assault When Risk of Harm to Innocent",

    # ==========================================
    # CHAPTER V - OF ABETMENT (Sections 107-120)
    # ==========================================
    "107": "Abetment of a Thing (Instigation, Conspiracy, Aid)",
    "108": "Abettor Defined",
    "108-A": "Abetment in Pakistan of Offences Outside Pakistan",
    "109": "Punishment of Abetment If Act Abetted Is Committed",
    "110": "Punishment of Abetment If Person Abetted Acts with Different Intention",
    "111": "Liability of Abettor When One Act Abetted and Different Act Done",
    "112": "Abettor Liable to Cumulative Punishment for Act Abetted and Act Done",
    "113": "Liability of Abettor for Effect Caused by Act Different from Intended",
    "114": "Abettor Present When Offence Is Committed",
    "115": "Abetment of Offence Punishable with Death or Life Imprisonment (If Not Committed)",
    "116": "Abetment of Offence Punishable with Imprisonment (If Not Committed)",
    "117": "Abetting Commission of Offence by Public or by More Than Ten Persons",
    "118": "Concealing Design to Commit Offence Punishable with Death or Life Imprisonment",
    "119": "Public Servant Concealing Design to Commit Offence He Must Prevent",
    "120": "Concealing Design to Commit Offence Punishable with Imprisonment",

    # ==========================================
    # CHAPTER V-A - CRIMINAL CONSPIRACY (Sections 120-A, 120-B)
    # ==========================================
    "120-A": "Definition of Criminal Conspiracy",
    "120-B": "Punishment of Criminal Conspiracy",

    # ==========================================
    # CHAPTER VI - OFFENCES AGAINST THE STATE (Sections 121-130)
    # ==========================================
    "121": "Waging or Attempting to Wage War Against Pakistan",
    "121-A": "Conspiracy to Commit Offences Against the State",
    "122": "Collecting Arms etc. with Intention of Waging War Against Pakistan",
    "123": "Concealing with Intent to Facilitate Design to Wage War",
    "123-A": "Condemning Creation of Pakistan / Advocating Abolition of Sovereignty",
    "123-B": "Defiling or Removing National Flag of Pakistan",
    "124": "Assaulting President or Governor to Compel or Restrain Lawful Power",
    "124-A": "Sedition",
    "125": "Waging War Against Power in Alliance with Pakistan",
    "126": "Committing Depredation on Territories of Power at Peace with Pakistan",
    "127": "Receiving Property Taken by War or Depredation",
    "128": "Public Servant Voluntarily Allowing Prisoner of State or War to Escape",
    "129": "Public Servant Negligently Suffering Prisoner to Escape",
    "130": "Aiding Escape of, Rescuing or Harbouring State/War Prisoner",

    # ==========================================
    # CHAPTER VII - OFFENCES RELATING TO ARMY, NAVY AND AIR FORCE (Sections 131-140)
    # ==========================================
    "131": "Abetting Mutiny or Attempting to Seduce Soldier/Sailor/Airman from Duty",
    "132": "Abetment of Mutiny (If Mutiny Is Committed)",
    "133": "Abetment of Assault by Soldier on Superior Officer",
    "134": "Abetment of Assault by Soldier on Superior Officer (If Committed)",
    "135": "Abetment of Desertion of Soldier, Sailor or Airman",
    "136": "Harbouring Deserter",
    "137": "Deserter Concealed on Merchant Vessel Through Negligence of Master",
    "138": "Abetment of Act of Insubordination by Soldier/Sailor/Airman",
    "139": "Persons Subject to Certain Military Acts",
    "140": "Wearing Garb or Carrying Token Used by Soldier/Sailor/Airman",

    # ==========================================
    # CHAPTER VIII - OFFENCES AGAINST PUBLIC TRANQUILLITY (Sections 141-160)
    # ==========================================
    "141": "Unlawful Assembly",
    "142": "Being Member of Unlawful Assembly",
    "143": "Punishment for Being Member of Unlawful Assembly",
    "144": "Joining Unlawful Assembly Armed with Deadly Weapon",
    "145": "Joining or Continuing in Unlawful Assembly After Command to Disperse",
    "146": "Rioting",
    "147": "Punishment for Rioting",
    "148": "Rioting Armed with Deadly Weapon",
    "149": "Every Member of Unlawful Assembly Guilty of Offence Committed in Common Object",
    "150": "Hiring or Conniving at Hiring of Persons to Join Unlawful Assembly",
    "151": "Knowingly Joining Assembly of Five or More After Command to Disperse",
    "152": "Assaulting or Obstructing Public Servant When Suppressing Riot",
    "153": "Wantonly Giving Provocation with Intent to Cause Riot",
    "153-A": "Promoting Enmity Between Different Groups",
    "153-B": "Inducing Students to Take Part in Political Activity",
    "154": "Owner/Occupier of Land Where Unlawful Assembly Held",
    "155": "Liability of Person for Whose Benefit Riot Is Committed",
    "156": "Liability of Agent of Owner/Occupier for Whose Benefit Riot Is Committed",
    "157": "Harbouring Persons Hired for Unlawful Assembly",
    "158": "Being Hired to Take Part in Unlawful Assembly or Riot",
    "159": "Affray (Fighting in Public Place)",
    "160": "Punishment for Committing Affray",

    # ==========================================
    # CHAPTER IX - OFFENCES BY OR RELATING TO PUBLIC SERVANTS (Sections 161-171)
    # ==========================================
    "161": "Public Servant Taking Bribe / Gratification (Corruption)",
    "162": "Taking Gratification to Influence Public Servant by Corrupt Means",
    "163": "Taking Gratification for Exercise of Personal Influence with Public Servant",
    "164": "Punishment for Abetment of Bribery by Public Servant",
    "165": "Public Servant Obtaining Valuable Thing Without Consideration",
    "165-A": "Punishment for Abetment of Offences Under Sections 161 and 165",
    "165-B": "Certain Abettors Excepted (Induced/Coerced to Give Bribe)",
    "166": "Public Servant Disobeying Law with Intent to Cause Injury",
    "167": "Public Servant Framing Incorrect Document with Intent to Cause Injury",
    "168": "Public Servant Unlawfully Engaging in Trade",
    "169": "Public Servant Unlawfully Buying or Bidding for Property",
    "170": "Personating a Public Servant",
    "171": "Wearing Garb or Carrying Token Used by Public Servant with Fraudulent Intent",

    # ==========================================
    # CHAPTER IX-A - OFFENCES RELATING TO ELECTIONS (Sections 171-A to 171-J)
    # ==========================================
    "171-A": "Candidate and Electoral Right Defined",
    "171-B": "Bribery at Elections",
    "171-C": "Undue Influence at Election",
    "171-D": "Personation at Elections",
    "171-E": "Punishment for Bribery at Election",
    "171-F": "Punishment for Undue Influence or Personation at Election",
    "171-G": "False Statement in Connection with Election",
    "171-H": "Illegal Payments in Connection with Election",
    "171-I": "Failure to Keep Election Accounts",
    "171-J": "Inducing Person Not to Participate in Election or Referendum",

    # ==========================================
    # CHAPTER X - CONTEMPT OF LAWFUL AUTHORITY OF PUBLIC SERVANTS (Sections 172-190)
    # ==========================================
    "172": "Absconding to Avoid Service of Summons or Proceeding",
    "173": "Preventing Service of Summons or Other Proceeding",
    "174": "Non-Attendance in Obedience to Order from Public Servant",
    "175": "Omission to Produce Document to Public Servant",
    "176": "Omission to Give Notice or Information to Public Servant",
    "177": "Furnishing False Information",
    "178": "Refusing Oath or Affirmation When Required by Public Servant",
    "179": "Refusing to Answer Public Servant Authorised to Question",
    "180": "Refusing to Sign Statement",
    "181": "False Statement on Oath or Affirmation to Public Servant",
    "182": "False Information to Cause Public Servant to Use Lawful Power to Injure Another",
    "183": "Resistance to Taking of Property by Lawful Authority",
    "184": "Obstructing Sale of Property by Authority of Public Servant",
    "185": "Illegal Purchase or Bid for Property Offered for Sale by Public Servant",
    "186": "Obstructing Public Servant in Discharge of Public Functions",
    "187": "Omission to Assist Public Servant When Bound by Law",
    "188": "Disobedience to Order Duly Promulgated by Public Servant",
    "189": "Threat of Injury to Public Servant",
    "190": "Threat of Injury to Induce Person to Refrain from Applying for Protection",

    # ==========================================
    # CHAPTER XI - FALSE EVIDENCE AND OFFENCES AGAINST PUBLIC JUSTICE (Sections 191-229)
    # ==========================================
    "191": "Giving False Evidence",
    "192": "Fabricating False Evidence",
    "193": "Punishment for Giving or Fabricating False Evidence",
    "194": "Giving or Fabricating False Evidence to Procure Conviction of Capital Offence",
    "195": "Giving or Fabricating False Evidence to Procure Conviction of Non-Capital Offence",
    "195-A": "Threatening or Inducing Person to Give False Evidence",
    "196": "Using Evidence Known to Be False",
    "197": "Issuing or Signing False Certificate",
    "198": "Using as True a Certificate Known to Be False",
    "199": "False Statement Made in Declaration Which is by Law Receivable as Evidence",
    "200": "Using as True Such Declaration Known to Be False",
    "201": "Causing Disappearance of Evidence or Giving False Information to Screen Offender",
    "202": "Intentional Omission to Give Information of Offence by Person Bound to Inform",
    "203": "Giving False Information Respecting Offence Committed",
    "204": "Destruction of Document to Prevent Its Production as Evidence",
    "205": "False Personation for Purpose of Act or Proceeding in Suit",
    "206": "Fraudulent Removal or Concealment of Property to Prevent Seizure",
    "207": "Fraudulent Claim to Property to Prevent Seizure",
    "208": "Fraudulently Suffering Decree for Sum Not Due",
    "209": "Dishonestly Making False Claim in Court",
    "210": "Fraudulently Obtaining Decree for Sum Not Due",
    "211": "False Charge of Offence Made with Intent to Injure",
    "212": "Harbouring Offender",
    "213": "Taking Gift to Screen Offender from Punishment",
    "214": "Offering Gift or Restoration of Property in Consideration of Screening Offender",
    "215": "Taking Gift to Help Recover Stolen Property",
    "216": "Harbouring Offender Who Has Escaped or Whose Apprehension Has Been Ordered",
    "216-A": "Penalty for Harbouring Robbers or Dacoits",
    "217": "Public Servant Disobeying Direction of Law to Render Assistance to Person",
    "218": "Public Servant Framing Incorrect Record with Intent to Save Person from Punishment",
    "219": "Public Servant in Judicial Proceeding Corruptly Making Report Contrary to Law",
    "220": "Commitment for Trial or Confinement by Person Having Authority Who Knows It Contrary to Law",
    "221": "Intentional Omission to Apprehend on Part of Public Servant Bound to Apprehend",
    "222": "Intentional Omission to Apprehend on Part of Public Servant Bound to Apprehend (Capital Offence)",
    "223": "Escape from Confinement Negligently Suffered by Public Servant",
    "224": "Resistance or Obstruction by Person to His Lawful Apprehension",
    "225": "Resistance or Obstruction to Lawful Apprehension of Another Person",
    "225-A": "Omission to Apprehend or Suffer Other Persons to Escape (Cases Not Covered)",
    "225-B": "Resistance or Obstruction to Lawful Apprehension (Penalty)",
    "226": "Unlawful Return from Transportation",
    "227": "Violation of Condition of Remission of Punishment",
    "228": "Intentional Insult or Interruption to Public Servant Sitting in Judicial Proceeding",
    "229": "Personation of Juror or Assessor",

    # ==========================================
    # CHAPTER XII - OFFENCES RELATING TO COIN AND GOVERNMENT STAMPS (Sections 230-263A)
    # ==========================================
    "230": "Coin Defined",
    "231": "Counterfeiting Coin",
    "232": "Counterfeiting Pakistani Coin",
    "233": "Making or Selling Instrument for Counterfeiting Coin",
    "234": "Making or Selling Instrument for Counterfeiting Pakistani Coin",
    "235": "Possession of Instrument or Material for Counterfeiting Coin",
    "236": "Abetting in Pakistan Counterfeiting of Coin Outside Pakistan",
    "237": "Import or Export of Counterfeit Coin",
    "238": "Import or Export of Counterfeits of Pakistani Coin",
    "239": "Delivery of Coin Possessed with Knowledge That It Is Counterfeit",
    "240": "Delivery of Pakistani Coin Possessed with Knowledge That It Is Counterfeit",
    "241": "Delivery of Coin as Genuine Which is Known to Be Altered",
    "242": "Possession of Counterfeit Coin by Person Who Knew It Was Counterfeit When Received",
    "243": "Possession of Pakistani Counterfeit Coin Known Counterfeit When Received",
    "244": "Employee of Mint Causing Coin to Be of Different Weight or Composition",
    "245": "Unlawfully Taking Coin from Mint",
    "246": "Fraudulently or Dishonestly Diminishing Weight or Altering Composition of Coin",
    "247": "Fraudulently or Dishonestly Diminishing Weight or Altering Composition of Pakistani Coin",
    "248": "Altering Appearance of Coin to Pass as Higher Value",
    "249": "Altering Appearance of Pakistani Coin to Pass as Higher Value",
    "250": "Delivery of Altered Coin Knowing It to Be Altered",
    "251": "Delivery of Pakistani Altered Coin Knowing It to Be Altered",
    "252": "Possession of Coin by Person Who Knew It Altered When Received",
    "253": "Possession of Pakistani Altered Coin Known Altered When Received",
    "254": "Delivery of Coin as Genuine Which Person Knows to Be Altered",
    "255": "Counterfeiting Government Stamp",
    "255-A": "Making or Selling Instrument for Counterfeiting Government Stamp",
    "256": "Having Possession of Instrument for Counterfeiting Government Stamp",
    "257": "Making or Selling Instrument for Making Document Resembling Government Stamp",
    "258": "Sale of Counterfeit Government Stamp",
    "259": "Having Possession of Counterfeit Government Stamp",
    "260": "Using as Genuine a Government Stamp Known to Be Counterfeit",
    "261": "Effacing Writing from Substance Bearing Government Stamp or Removing from Document",
    "262": "Using Government Stamp Known to Have Been Previously Used",
    "263": "Erasure of Mark Denoting Stamp Has Been Used",
    "263-A": "Prohibition of Fictitious Stamps",

    # ==========================================
    # CHAPTER XIII - OFFENCES RELATING TO WEIGHTS AND MEASURES (Sections 264-267)
    # ==========================================
    "264": "Fraudulent Use of False Instrument for Weighing",
    "265": "Fraudulent Use of False Weight or Measure",
    "266": "Being in Possession of False Weight or Measure for Fraudulent Use",
    "267": "Making or Selling False Weight or Measure for Fraudulent Use",

    # ==========================================
    # CHAPTER XIV - OFFENCES AFFECTING PUBLIC HEALTH, SAFETY, CONVENIENCE, DECENCY AND MORALS (Sections 268-294B)
    # ==========================================
    "268": "Public Nuisance",
    "269": "Negligent Act Likely to Spread Infection of Disease Dangerous to Life",
    "270": "Malignant Act Likely to Spread Infection of Disease Dangerous to Life",
    "271": "Disobedience to Quarantine Rule",
    "272": "Adulteration of Food or Drink Intended for Sale",
    "273": "Sale of Noxious Food or Drink",
    "274": "Adulteration of Drugs",
    "275": "Sale of Adulterated Drugs",
    "276": "Sale of Drug as Different Drug or Preparation",
    "277": "Fouling Water of Public Spring or Reservoir",
    "278": "Making Atmosphere Noxious to Health",
    "279": "Rash Driving or Riding on Public Way",
    "280": "Rash Navigation of Vessel",
    "281": "Exhibition of False Light, Mark or Buoy",
    "282": "Conveying Person by Water for Hire in Unsafe or Overloaded Vessel",
    "283": "Danger or Obstruction in Public Way or Line of Navigation",
    "284": "Negligent Conduct with Respect to Poisonous Substance",
    "285": "Negligent Conduct with Respect to Fire or Combustible Matter",
    "286": "Negligent Conduct with Respect to Explosive Substance",
    "287": "Negligent Conduct with Respect to Machinery",
    "288": "Negligent Conduct with Respect to Pulling Down or Repairing Building",
    "289": "Negligent Conduct with Respect to Animal",
    "290": "Punishment for Public Nuisance (Cases Not Otherwise Provided For)",
    "291": "Continuance of Nuisance After Injunction to Discontinue",
    "292": "Sale of Obscene Books, Etc.",
    "293": "Sale of Obscene Objects to Young Person",
    "294": "Obscene Acts and Songs",
    "294-A": "Keeping a Lottery Office",
    "294-B": "Gambling",

    # ==========================================
    # CHAPTER XV - OFFENCES RELATING TO RELIGION (Sections 295-298C)
    # ==========================================
    "295": "Injuring or Defiling Place of Worship with Intent to Insult Religion",
    "295-A": "Deliberate and Malicious Acts Intended to Outrage Religious Feelings",
    "295-B": "Defiling the Holy Quran",
    "295-C": "Use of Derogatory Remarks Against Prophet Muhammad (PBUH) (Blasphemy)",
    "296": "Disturbing Religious Assembly",
    "297": "Trespassing on Burial Places",
    "298": "Uttering Words with Deliberate Intent to Wound Religious Feelings",
    "298-A": "Use of Derogatory Remarks Against Holy Personages",
    "298-B": "Misuse of Epithets, Descriptions and Titles Reserved for Holy Personages (Ahmadi)",
    "298-C": "Ahmadi Calling Himself Muslim or Preaching His Faith (Ahmadi Blasphemy)",

    # ==========================================
    # CHAPTER XVI - OFFENCES AFFECTING THE HUMAN BODY
    # Of Offences Affecting Life (Sections 299-338H)
    # ==========================================
    "299": "Definition of Culpable Homicide",
    "300": "Definition of Murder (Qatl-i-Amd)",
    "301": "Culpable Homicide by Causing Death of Person Other Than Intended",
    "302": "Murder (Qatl-i-Amd) - Punishment (Death/Life Imprisonment)",
    "302-A": "Punishment for Concealing the Birth of a Child by Secret Disposal of Dead Body",
    "302-B": "Punishment for Murder Committed in the Name or on Pretext of Honour (Honour Killing)",
    "302-C": "Offences Not to Be Compounded (Honour Killing Cannot Be Pardoned)",
    "303": "Punishment for Murder by Life-Convict",
    "304": "Punishment for Culpable Homicide Not Amounting to Murder (Qatl-i-Khata)",
    "304-A": "Causing Death by Negligence",
    "305": "Abetment of Suicide of Child or Insane Person",
    "306": "Abetment of Suicide",
    "307": "Attempt to Murder",
    "308": "Attempt to Commit Culpable Homicide",
    "309": "Attempt to Commit Suicide",
    "310": "Thug (Definition)",
    "311": "Punishment for Thug",

    # Qisas and Diyat Provisions (Sections 299-338)
    "312": "Causing Miscarriage (Isqat-i-Haml)",
    "313": "Causing Miscarriage Without Consent of Woman",
    "314": "Death Caused by Act Done with Intent to Cause Miscarriage",
    "315": "Act Done with Intent to Prevent Child Being Born Alive or to Cause Death After Birth",
    "316": "Causing Death of Quick Unborn Child by Act Amounting to Culpable Homicide",
    "317": "Exposure and Abandonment of Child Under Twelve by Parent or Guardian",
    "318": "Concealment of Birth by Secret Disposal of Dead Body",
    "319": "Definition of Hurt",
    "319-A": "Itlaf-i-Udw (Destroying or Permanently Impairing Organ/Limb)",
    "319-B": "Itlaf-i-Salahiyyat-i-Udw (Permanently Impairing Functioning of Organ)",
    "320": "Grievous Hurt",
    "321": "Voluntarily Causing Hurt",
    "322": "Itlaf-i-Udw (Destroying Limb/Organ - Punishment)",
    "323": "Punishment for Voluntarily Causing Hurt",
    "324": "Attempt to Murder / Voluntarily Causing Hurt by Dangerous Weapons or Means",
    "325": "Punishment for Voluntarily Causing Grievous Hurt",
    "326": "Voluntarily Causing Grievous Hurt by Dangerous Weapons or Means",
    "327": "Voluntarily Causing Hurt to Extort Property or to Compel Illegal Act",
    "328": "Causing Hurt by Means of Poison etc. with Intent to Commit Offence",
    "329": "Voluntarily Causing Grievous Hurt to Extort Property or Compel Illegal Act",
    "330": "Voluntarily Causing Hurt to Extort Confession or Information",
    "331": "Voluntarily Causing Grievous Hurt to Extort Confession or Information",
    "332": "Voluntarily Causing Hurt to Deter Public Servant from Duty",
    "333": "Voluntarily Causing Grievous Hurt to Deter Public Servant from Duty",
    "334": "Voluntarily Causing Hurt on Provocation",
    "335": "Voluntarily Causing Grievous Hurt on Grave and Sudden Provocation",
    "336": "Act Endangering Life or Personal Safety of Others (Rash/Negligent)",
    "337": "Causing Hurt by Act Endangering Life or Personal Safety",

    # 337 Sub-sections (Hurt/Injury Compensation - Arsh/Daman)
    "337-A": "Shajjah (Hurt on Head or Face) - Types and Punishment",
    "337-A(i)": "Shajjah-i-Khafifah (Scratch/Bruise on Head/Face)",
    "337-A(ii)": "Shajjah-i-Mudihah (Hurt Exposing Bone of Head/Face)",
    "337-A(iii)": "Shajjah-i-Hashimah (Hurt Breaking Bone of Head/Face)",
    "337-A(iv)": "Shajjah-i-Munaqqilah (Hurt Displacing Bone of Head/Face)",
    "337-A(v)": "Shajjah-i-Ammah (Hurt Exposing Membrane of Brain)",
    "337-A(vi)": "Shajjah-i-Damighah (Hurt Rupturing Membrane of Brain)",
    "337-D": "Jurh (Hurt on Body Other Than Head/Face)",
    "337-F": "Hurt by Rash or Negligent Act (Causing Fracture/Dislocation)",
    "337-F(i)": "Causing Hurt Not Liable to Qisas (Arsh - Compensation)",
    "337-F(ii)": "Causing Hurt by Rash/Negligent Driving",
    "337-F(iii)": "Hurt Causing Miscarriage",
    "337-G": "Punishment for Hurt by Corrosive Substance (Acid Attack)",
    "337-H": "Hurt Not Otherwise Provided For",
    "337-H(i)": "Badal-i-Sulh (Compensation by Agreement)",
    "337-H(ii)": "Hurt Not Liable to Arsh (Tazir Punishment)",

    # Wrongful Restraint and Confinement (Sections 339-348)
    "339": "Wrongful Restraint",
    "340": "Wrongful Confinement",
    "341": "Punishment for Wrongful Restraint",
    "342": "Punishment for Wrongful Confinement",
    "343": "Wrongful Confinement for Three or More Days",
    "344": "Wrongful Confinement for Ten or More Days",
    "345": "Wrongful Confinement of Person for Whose Liberation Writ Has Been Issued",
    "346": "Wrongful Confinement in Secret",
    "347": "Wrongful Confinement to Extort Property or Compel Illegal Act",
    "348": "Wrongful Confinement to Extort Confession or Information",

    # Criminal Force and Assault (Sections 349-358)
    "349": "Force",
    "350": "Criminal Force",
    "351": "Assault",
    "352": "Punishment for Assault or Criminal Force Otherwise Than on Grave Provocation",
    "353": "Assault or Criminal Force to Deter Public Servant from Discharge of Duty",
    "354": "Assault or Criminal Force to Woman with Intent to Outrage Her Modesty",
    "354-A": "Assault or Use of Criminal Force to Woman and Stripping Her of Clothes",
    "355": "Assault or Criminal Force with Intent to Dishonour Person",
    "356": "Assault or Criminal Force in Attempt to Commit Theft of Property",
    "357": "Assault or Criminal Force in Attempt to Wrongfully Confine a Person",
    "358": "Assault or Criminal Force on Grave and Sudden Provocation",

    # Kidnapping, Abduction and Slavery (Sections 359-374)
    "359": "Kidnapping (Two Types Defined)",
    "360": "Kidnapping from Pakistan",
    "361": "Kidnapping from Lawful Guardianship",
    "362": "Abduction",
    "363": "Punishment for Kidnapping",
    "363-A": "Kidnapping or Abducting Person for Ransom",
    "364": "Kidnapping or Abducting in Order to Murder",
    "364-A": "Kidnapping or Abducting Person Under Age of Fourteen",
    "365": "Kidnapping or Abducting with Intent to Secretly and Wrongfully Confine",
    "365-A": "Kidnapping or Abducting for Extortion (Ransom)",
    "365-B": "Kidnapping, Abducting or Inducing Woman to Compel for Marriage",
    "366": "Kidnapping, Abducting or Inducing Woman to Compel Her Marriage",
    "366-A": "Procuration of Minor Girl",
    "366-B": "Importation of Girl from Foreign Country",
    "367": "Kidnapping or Abducting in Order to Subject Person to Grievous Hurt or Slavery",
    "368": "Wrongfully Concealing or Keeping in Confinement Kidnapped Person",
    "369": "Kidnapping or Abducting Child Under Ten Years with Intent to Steal",
    "370": "Buying or Disposing of Any Person as a Slave",
    "371": "Habitual Dealing in Slaves",
    "372": "Selling Minor for Purposes of Prostitution",
    "373": "Buying Minor for Purposes of Prostitution",
    "374": "Unlawful Compulsory Labour",

    # Sexual Offences (Sections 375-377)
    "375": "Rape (Zina-bil-Jabr) Defined",
    "376": "Punishment for Rape",
    "377": "Unnatural Offences (Sodomy/Bestiality)",

    # ==========================================
    # CHAPTER XVII - OFFENCES AGAINST PROPERTY
    # Of Theft (Sections 378-382)
    # ==========================================
    "378": "Theft Defined",
    "379": "Punishment for Theft",
    "380": "Theft in Dwelling House, Building, Tent or Vessel",
    "381": "Theft by Clerk or Servant of Property in Possession of Master",
    "382": "Theft After Preparation Made for Causing Death, Hurt or Restraint",

    # Of Extortion (Sections 383-389)
    "383": "Extortion Defined",
    "384": "Punishment for Extortion",
    "385": "Putting Person in Fear of Injury in Order to Commit Extortion",
    "386": "Extortion by Putting Person in Fear of Death or Grievous Hurt",
    "387": "Putting Person in Fear of Death or Grievous Hurt in Order to Commit Extortion",
    "388": "Extortion by Threat of Accusation of Unnatural Offence, etc.",
    "389": "Putting Person in Fear of Accusation of Offence in Order to Commit Extortion",

    # Of Robbery and Dacoity (Sections 390-402)
    "390": "Robbery Defined",
    "391": "Dacoity (Gang Robbery) Defined",
    "392": "Punishment for Robbery",
    "393": "Attempt to Commit Robbery",
    "394": "Voluntarily Causing Hurt in Committing Robbery",
    "395": "Punishment for Dacoity (Gang Robbery)",
    "396": "Dacoity with Murder",
    "397": "Robbery or Dacoity with Attempt to Cause Death or Grievous Hurt",
    "398": "Attempt to Commit Robbery or Dacoity When Armed with Deadly Weapon",
    "399": "Making Preparation to Commit Dacoity",
    "400": "Punishment for Belonging to Gang of Dacoits",
    "401": "Punishment for Belonging to Gang of Thieves",
    "402": "Assembling for Purpose of Committing Dacoity",

    # Of Criminal Misappropriation of Property (Sections 403-404)
    "403": "Dishonest Misappropriation of Property",
    "404": "Dishonest Misappropriation of Property Possessed by Deceased Person",

    # Of Criminal Breach of Trust (Sections 405-409)
    "405": "Criminal Breach of Trust Defined",
    "406": "Punishment for Criminal Breach of Trust",
    "407": "Criminal Breach of Trust by Carrier, Wharfinger or Warehouse-Keeper",
    "408": "Criminal Breach of Trust by Clerk or Servant",
    "409": "Criminal Breach of Trust by Public Servant, Banker, Merchant or Agent",

    # Of Receiving Stolen Property (Sections 410-414)
    "410": "Stolen Property Defined",
    "411": "Dishonestly Receiving Stolen Property",
    "412": "Dishonestly Receiving Property Stolen in Dacoity",
    "413": "Habitually Dealing in Stolen Property",
    "414": "Assisting in Concealment of Stolen Property",

    # Of Cheating (Sections 415-420)
    "415": "Cheating Defined",
    "416": "Cheating by Personation",
    "417": "Punishment for Cheating",
    "418": "Cheating with Knowledge That Wrongful Loss May Be Caused to Person Whose Interest Offender Bound to Protect",
    "419": "Punishment for Cheating by Personation",
    "420": "Cheating and Dishonestly Inducing Delivery of Property (Fraud)",

    # Of Fraudulent Deeds and Dispositions of Property (Sections 421-424)
    "421": "Dishonest or Fraudulent Removal or Concealment of Property",
    "422": "Dishonestly or Fraudulently Preventing Debt Being Available for Creditors",
    "423": "Dishonest or Fraudulent Execution of Deed of Transfer Containing False Statement",
    "424": "Dishonest or Fraudulent Removal or Concealment of Property",

    # Of Mischief (Sections 425-440)
    "425": "Mischief Defined",
    "426": "Punishment for Mischief",
    "427": "Mischief Causing Damage to Amount of Fifty Rupees or More",
    "428": "Mischief by Killing or Maiming Animal (Value Ten Rupees or More)",
    "429": "Mischief by Killing or Maiming Cattle, etc. (Any Value)",
    "430": "Mischief by Injury to Works of Irrigation or by Wrongfully Diverting Water",
    "431": "Mischief by Injury to Public Road, Bridge, River or Channel",
    "432": "Mischief by Causing Inundation or Obstruction to Public Drainage",
    "433": "Mischief by Destroying, Moving or Rendering Useless Lighthouse or Sea-Mark",
    "434": "Mischief by Destroying or Moving Landmark Fixed by Public Authority",
    "435": "Mischief by Fire or Explosive Substance with Intent to Cause Damage",
    "436": "Mischief by Fire or Explosive Substance with Intent to Destroy House (Arson)",
    "437": "Mischief with Intent to Destroy or Make Unsafe Vessel in Dock",
    "438": "Punishment for Mischief Described in Section 437 When Committed by Fire/Explosive",
    "439": "Punishment for Intentionally Running Vessel Aground or Ashore with Intent to Commit Theft",
    "440": "Mischief Committed After Preparation for Causing Death or Hurt",

    # Of Criminal Trespass (Sections 441-462)
    "441": "Criminal Trespass Defined",
    "442": "House-Trespass Defined",
    "443": "Lurking House-Trespass",
    "444": "Lurking House-Trespass by Night",
    "445": "House-Breaking Defined",
    "446": "House-Breaking by Night",
    "447": "Punishment for Criminal Trespass",
    "448": "Punishment for House-Trespass",
    "449": "House-Trespass in Order to Commit Offence Punishable with Death",
    "450": "House-Trespass to Commit Offence Punishable with Life Imprisonment",
    "451": "House-Trespass to Commit Offence Punishable with Imprisonment",
    "452": "House-Trespass After Preparation for Hurt, Assault or Wrongful Restraint",
    "453": "Punishment for Lurking House-Trespass",
    "454": "Lurking House-Trespass to Commit Offence Punishable with Imprisonment",
    "455": "Lurking House-Trespass After Preparation for Hurt, Assault, etc.",
    "456": "Punishment for Lurking House-Trespass by Night",
    "457": "Lurking House-Trespass by Night to Commit Offence (Burglary at Night)",
    "458": "Lurking House-Trespass by Night After Preparation for Hurt (Night Burglary with Violence)",
    "459": "Grievous Hurt Caused While Committing Lurking House-Trespass",
    "460": "All Persons Jointly Concerned in Lurking House-Trespass by Night",
    "461": "Dishonestly Breaking Open Receptacle Containing Property",
    "462": "Punishment for Same Offence When Committed by Person Entrusted with Custody",

    # ==========================================
    # CHAPTER XVIII - OFFENCES RELATING TO DOCUMENTS AND PROPERTY MARKS (Sections 463-489F)
    # ==========================================
    "463": "Forgery Defined",
    "464": "Making a False Document",
    "465": "Punishment for Forgery",
    "466": "Forgery of Record of Court or Public Register",
    "467": "Forgery of Valuable Security, Will, or Authority to Make Payment",
    "468": "Forgery for Purpose of Cheating",
    "469": "Forgery for Purpose of Harming Reputation",
    "470": "Forged Document Defined",
    "471": "Using as Genuine a Forged Document",
    "472": "Making or Possessing Counterfeit Seal, Plate, etc. for Forging",
    "473": "Making or Possessing Counterfeit Seal, Plate, etc. for Forging Valuable Security",
    "474": "Having Possession of Document Known to Be Forged with Intent to Use as Genuine",
    "475": "Counterfeiting Device or Mark Used for Authenticating Documents",
    "476": "Counterfeiting Device or Mark Used by Public Servant",
    "477": "Fraudulent Cancellation, Destruction, etc. of Will, Authority to Adopt, etc.",
    "477-A": "Falsification of Accounts",
    "478": "Trade Mark and Property Mark Defined",
    "479": "Counterfeit Trade/Property Mark Defined",
    "480": "Using a False Property Mark",
    "481": "Using a False Trade Mark",
    "482": "Punishment for Using False Property Mark",
    "483": "Counterfeiting a Property Mark Used by Another",
    "484": "Counterfeiting a Trade Mark Used by Another",
    "485": "Making or Possessing Any Instrument for Counterfeiting a Property Mark",
    "486": "Selling Goods Marked with Counterfeit Property Mark",
    "487": "Making False Mark Upon Any Receptacle Containing Goods",
    "488": "Punishment for Making Use of Counterfeit Trade Mark",
    "489": "Tampering with Property Mark with Intent to Cause Damage or Injury",
    "489-A": "Counterfeiting Currency Notes or Bank Notes",
    "489-B": "Using as Genuine Forged or Counterfeit Currency Notes or Bank Notes",
    "489-C": "Possession of Forged or Counterfeit Currency Notes or Bank Notes",
    "489-D": "Making or Possessing Instruments or Materials for Forging Currency Notes",
    "489-E": "Making or Using Documents Resembling Currency Notes or Bank Notes",
    "489-F": "Dishonestly Issuing a Cheque (Bounced Cheque / Bad Cheque)",

    # ==========================================
    # CHAPTER XIX - CRIMINAL BREACH OF CONTRACTS OF SERVICE (Sections 490-492)
    # ==========================================
    "490": "Breach of Contract of Service During Voyage or Journey",
    "491": "Breach of Contract to Attend on or Supply Wants of Helpless Person",
    "492": "Breach of Contract to Serve at Distant Place",

    # ==========================================
    # CHAPTER XX - OFFENCES RELATING TO MARRIAGE (Sections 493-498)
    # ==========================================
    "493": "Cohabitation Caused by Man Deceitfully Inducing Belief of Lawful Marriage",
    "494": "Marrying Again During Lifetime of Husband or Wife (Bigamy)",
    "495": "Same Offence with Concealment of Former Marriage",
    "496": "Marriage Ceremony Fraudulently Gone Through Without Lawful Marriage",
    "497": "Adultery",
    "498": "Enticing or Taking Away or Detaining Married Woman with Criminal Intent",

    # ==========================================
    # CHAPTER XX-A - OFFENCES AGAINST WOMEN (Sections 498-A, 498-B, 498-C)
    # ==========================================
    "498-A": "Cruelty to Woman by Husband or His Relatives",
    "498-B": "Demanding Dowry from Woman (Domestic Violence/Dowry Related)",
    "498-C": "Prohibition of Giving a Female in Marriage to Settle Dispute (Vani/Swara)",

    # ==========================================
    # CHAPTER XXI - DEFAMATION (Sections 499-502)
    # ==========================================
    "499": "Defamation Defined",
    "500": "Punishment for Defamation",
    "501": "Printing or Engraving Matter Known to Be Defamatory",
    "502": "Sale of Printed or Engraved Substance Containing Defamatory Matter",

    # ==========================================
    # CHAPTER XXII - CRIMINAL INTIMIDATION, INSULT AND ANNOYANCE (Sections 503-510)
    # ==========================================
    "503": "Criminal Intimidation",
    "504": "Intentional Insult with Intent to Provoke Breach of Peace",
    "505": "Statements Conducing to Public Mischief",
    "506": "Punishment for Criminal Intimidation (Threats)",
    "507": "Criminal Intimidation by Anonymous Communication",
    "508": "Act Caused by Inducing Person to Believe He Will Be Object of Divine Displeasure",
    "509": "Word, Gesture or Act Intended to Insult Modesty of a Woman",
    "510": "Misconduct in Public by a Drunken Person",

    # ==========================================
    # CHAPTER XXIII - OF ATTEMPTS TO COMMIT OFFENCES (Section 511)
    # ==========================================
    "511": "Punishment for Attempting to Commit Offences Punishable with Imprisonment",
}


# ==========================================
# ANTI-TERRORISM ACT (ATA) 1997 - Sections
# ==========================================
ATA_SECTIONS = {
    "1": "Short Title, Extent and Commencement",
    "2": "Definitions",
    "3": "Application of the Act",
    "4": "Cognizance of Scheduled Offences",
    "5": "Power to Transfer Cases",
    "6": "Terrorism Defined (Acts of Violence, Intimidation, Creating Fear/Insecurity)",
    "7": "Punishment for Acts of Terrorism (Death / Life Imprisonment / 5-20 Years RI)",
    "7-A": "Enhancement of Punishment Under Other Laws (Terrorism Context)",
    "7-B": "Punishment for Facilitating Terrorism",
    "8": "Prohibition of Acts Intended to Stir Up Sectarian Hatred",
    "9": "Proscribed Organizations",
    "10": "Penalty for Fund-Raising for Proscribed Organizations",
    "11": "Offences Relating to Membership of Proscribed Organizations",
    "11-A": "Prohibition Against Printing/Publishing Material of Proscribed Organizations",
    "11-B": "Penalty for Arranging Meetings of Proscribed Organizations",
    "11-C": "Dealing in Property of Proscribed Organizations",
    "11-D": "Use of Premises for Proscribed Organizations",
    "11-E": "Penalty for Persons Involved in Terrorist Financing",
    "11-EE": "Penalty for Providing Services to Proscribed Organizations",
    "11-F": "Penalty for Providing Weapons to Terrorist/Proscribed Organization",
    "11-G": "Penalty for Assisting/Harboring Wanted Terrorists",
    "11-GG": "Penalty for Accepting Money/Aid from Foreign Sources for Terrorism",
    "11-H": "Punishment for Use of Explosives",
    "11-I": "Penalty for Cyber Terrorism",
    "11-J": "Penalty for Making/Possessing Explosive Substance",
    "11-K": "Penalty for Glorifying Terrorism",
    "11-L": "Penalty for Recruitment for Terrorism",
    "11-W": "Punishment for Kidnapping/Abduction for Ransom",
    "11-X": "Punishment for Hostage Taking",
    "12": "Penalty for Contravention of Provisions of the Act",
    "13": "Forfeiture of Proceeds/Property Derived from Terrorism",
    "14": "Power of Investigation",
    "15": "Protection of Witnesses",
    "16": "Anti-Terrorism Courts Established",
    "17": "Appointment of Judges of Anti-Terrorism Courts",
    "18": "Transfer of Cases to Anti-Terrorism Courts",
    "19": "Procedure and Powers of Anti-Terrorism Courts",
    "20": "Appeal and Revision",
    "21": "Time Limit for Completion of Trial",
    "21-H": "Power to Grant Bail",
    "21-I": "Offences Triable by Anti-Terrorism Courts",
    "25": "Power to Arrest Without Warrant",
    "27": "Power of Federal Government to Make Rules",
    "28": "Overriding Effect of the Act",
}

# ==========================================
# CONTROL OF NARCOTIC SUBSTANCES ACT (CNSA) 1997
# ==========================================
CNSA_SECTIONS = {
    "3": "Definitions (Narcotic Drugs, Psychotropic Substances)",
    "4": "Prohibition of Cultivation of Certain Plants (Cannabis, Opium Poppy, Coca)",
    "5": "Prohibition of Production/Manufacture of Narcotic Substances",
    "6": "Prohibition of Possession of Narcotic/Psychotropic Substances",
    "6-A": "Penalty for Possession of Controlled Substance - Small Quantity",
    "7": "Prohibition of Import/Export of Narcotic Substances",
    "8": "Prohibition of Trafficking in Narcotic/Psychotropic Substances",
    "9": "Punishment for Offences (Death/Life/14 Years Based on Quantity)",
    "9-A": "Enhanced Punishment for Trafficking Near Schools/Public Places",
    "9-B": "Punishment for Repeat Offenders",
    "9-C": "Punishment for Abetment",
    "10": "Forfeiture of Narcotic Property",
    "11": "Punishment for Occupier of Premises Used for Drug Offences",
    "12": "Vesting of Property in Federal/Provincial Government",
    "13": "Power to Freeze/Seize Property",
    "14": "Power of Search Without Warrant",
    "15": "Power to Arrest Without Warrant",
    "16": "Establishment of Special Courts",
    "20": "Presumption of Guilt (Possession)",
    "21": "Compounding of Offences",
    "22": "Power to Make Rules",
    "23": "Offence by Body Corporate",
    "24": "Protection of Informers",
    "25": "Offences to be Cognizable, Non-Bailable, Non-Compoundable",
    "68": "Prohibition of Cultivation of Cannabis/Opium (Detailed)",
    "77": "Punishment for Contravention (General)",
}

# ==========================================
# PAKISTAN ARMS ORDINANCE 1965
# ==========================================
ARMS_SECTIONS = {
    "3": "License Required for Manufacture/Sale/Possession of Arms",
    "4": "Prohibition of Sale to Certain Persons",
    "5": "Prohibition on Possession of Arms in Certain Places",
    "6": "Power to Prohibit Carrying of Arms",
    "7": "Penalty for Manufacture Without License",
    "8": "Penalty for Sale Without License",
    "9": "Penalty for Possession of Arms Without License",
    "10": "Penalty for Carrying Arms in Prohibited Areas",
    "11": "Penalty for Dealing in Prohibited Bore Arms",
    "12": "Penalty for Possession of Prohibited Bore Firearms",
    "13": "Punishment for Possession of Firearms/Ammunition Without License (3-7 Years)",
    "14": "Enhanced Punishment for Prohibited Bore (7-14 Years / Death if Used in Crime)",
    "15": "Punishment for Exhibiting/Brandishing Firearms in Public (Up to 3 Years)",
    "16": "Punishment for Firing in Inhabited Area (Up to 7 Years)",
    "17": "Power of Search and Seizure",
    "18": "Power to Arrest Without Warrant",
    "19": "Confiscation of Arms",
    "20": "Trial of Offences",
    "23": "Offences to be Cognizable and Non-Bailable",
}

# ==========================================
# HUDOOD ORDINANCES 1979
# ==========================================
HUDOOD_SECTIONS = {
    "4": "Punishment for Zina (Adultery/Fornication)",
    "5": "Punishment for Zina-bil-Jabr (Rape - Death/Life/25 Years)",
    "6": "Definition of Zina",
    "7": "Zina Liable to Hadd",
    "8": "Zina Liable to Tazir",
    "10": "Punishment for Qazf (False Accusation of Zina)",
    "11": "Proof of Qazf Liable to Hadd",
    "12": "Qazf Liable to Tazir",
    "17": "Punishment for Theft Liable to Hadd (Amputation of Hand)",
    "18": "Proof of Theft Liable to Hadd",
    "19": "Theft Liable to Tazir",
    "20": "Punishment for Dacoity/Robbery Liable to Hadd",
}

# ==========================================
# PREVENTION OF ELECTRONIC CRIMES ACT (PECA) 2016
# ==========================================
PECA_SECTIONS = {
    "2": "Definitions",
    "3": "Unauthorized Access to Information System (Up to 3 Months / Fine Rs.50,000)",
    "4": "Unauthorized Copying of Data (Up to 6 Months / Fine Rs.100,000)",
    "5": "Interference with Information System (Up to 2 Years / Fine Rs.500,000)",
    "6": "Unauthorized Access to Critical Infrastructure (Up to 3 Years / Fine Rs.1,000,000)",
    "7": "Glorification of Offence (Up to 5 Years / Fine Rs.10,000,000)",
    "8": "Preparation of Cyber Crime (Up to 2 Years / Fine Rs.500,000)",
    "9": "Cyber Terrorism (Up to 14 Years / Fine Rs.50,000,000)",
    "10": "Electronic Forgery (Up to 3 Years / Fine Rs.250,000)",
    "11": "Electronic Fraud (Up to 2 Years / Fine Rs.10,000,000)",
    "12": "Offences Against Modesty/Decency of Natural Person (Up to 5 Years / Fine Rs.5,000,000)",
    "13": "Child Pornography (Up to 7 Years / Fine Rs.5,000,000)",
    "14": "Malicious Code (Up to 5 Years / Fine Rs.5,000,000)",
    "15": "Cyber Stalking (Up to 3 Years / Fine Rs.1,000,000)",
    "16": "Spamming (Up to 3 Months / Fine Rs.50,000)",
    "17": "Spoofing (Up to 3 Years / Fine Rs.500,000)",
    "18": "Unauthorized Interception (Up to 2 Years / Fine Rs.500,000)",
    "19": "Offences Against Dignity of Natural Person (Up to 3 Years / Fine Rs.1,000,000)",
    "20": "Hate Speech (Up to 7 Years / Fine Rs.10,000,000)",
    "21": "Recruitment for Terrorism (Up to 7 Years)",
    "22": "Funding of Terrorism (Up to 7 Years / Fine Rs.5,000,000)",
    "23": "Aiding and Abetting Cyber Crime",
    "24": "Powers of Investigation",
    "25": "Powers of Court to Issue Warrants",
    "36": "Offences to be Cognizable, Bailable/Non-Bailable",
    "37": "Prosecution Sanctions",
}

# ==========================================
# EXPLOSIVE SUBSTANCES ACT 1908
# ==========================================
EXPLOSIVE_SECTIONS = {
    "3": "Punishment for Causing Explosion Likely to Endanger Life or Property",
    "4": "Punishment for Attempt to Cause Explosion",
    "5": "Punishment for Making/Possessing Explosive Substance",
    "6": "Punishment for Accessory to Offence Under This Act",
}

# ==========================================
# TELEGRAPH ACT 1885
# ==========================================
TELEGRAPH_SECTIONS = {
    "20": "Intentionally Damaging Telegraph Line or Equipment",
    "21": "Negligently Damaging Telegraph",
    "22": "Unlawfully Attempting to Learn Contents of Messages",
    "23": "Intentionally Intercepting/Detaining Telegraph Messages",
    "25": "Fraudulently Retaining Telegraph Message Not Intended for Recipient",
    "26": "Protection of Telegraph",
}

# ==========================================
# LOCAL AND SPECIAL LAWS (LSL) - Common Sections
# ==========================================
LSL_SECTIONS = {
    "3": "Loudspeaker Act - Violation of Loudspeaker/Sound Amplifier Restrictions",
    "4": "Loudspeaker Act - Penalty for Violation",
    "16": "Punjab Sound Systems Act - Restriction on Loudspeakers",
}

# ==========================================
# PROTECTION OF WOMEN (CRIMINAL LAWS AMENDMENT) ACT 2006
# ==========================================
WOMEN_PROTECTION_SECTIONS = {
    "365-B": "Kidnapping/Abduction/Inducing Woman to Compel for Marriage",
    "375": "Rape Defined",
    "376": "Punishment for Rape",
    "493-A": "Cohabitation Caused by Deceitfully Inducing Belief of Lawful Marriage",
}

# ==========================================
# Map of law prefixes to their dictionaries and display names
# ==========================================
LAW_MAPPINGS = {
    "ATA": {"dict": ATA_SECTIONS, "name": "ATA", "full_name": "Anti-Terrorism Act 1997"},
    "CNSA": {"dict": CNSA_SECTIONS, "name": "CNSA", "full_name": "Control of Narcotic Substances Act 1997"},
    "ARMS": {"dict": ARMS_SECTIONS, "name": "Arms", "full_name": "Pakistan Arms Ordinance 1965"},
    "HUDOOD": {"dict": HUDOOD_SECTIONS, "name": "Hudood", "full_name": "Hudood Ordinances 1979"},
    "PECA": {"dict": PECA_SECTIONS, "name": "PECA", "full_name": "Prevention of Electronic Crimes Act 2016"},
    "EXPLOSIVE": {"dict": EXPLOSIVE_SECTIONS, "name": "Explosive", "full_name": "Explosive Substances Act 1908"},
    "TELEGRAPH": {"dict": TELEGRAPH_SECTIONS, "name": "Telegraph", "full_name": "Telegraph Act 1885"},
    "LSL": {"dict": LSL_SECTIONS, "name": "LSL", "full_name": "Local and Special Laws"},
    "WPA": {"dict": WOMEN_PROTECTION_SECTIONS, "name": "WPA", "full_name": "Protection of Women Act 2006"},
}


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _lookup_in_dict(section_num: str, law_dict: dict) -> str:
    """Try to find a section number in a law dictionary with normalization."""
    import re
    section_num = section_num.strip().upper()

    # Exact match
    if section_num in law_dict:
        return law_dict[section_num]

    # Case-insensitive match
    for key, value in law_dict.items():
        if key.upper() == section_num:
            return value

    # Normalize hyphens
    normalized = section_num.replace(" - ", "-").replace("- ", "-").replace(" -", "-")
    if normalized in law_dict:
        return law_dict[normalized]

    # Try numeric + alpha sub-section (e.g., "11EE" -> "11-EE")
    match = re.match(r'^([0-9]+)\s*[-]?\s*([A-Za-z].*)?$', section_num)
    if match:
        num_part = match.group(1)
        alpha_part = match.group(2) or ""
        if alpha_part:
            candidate = f"{num_part}-{alpha_part.upper()}"
            if candidate in law_dict:
                return law_dict[candidate]
        if num_part in law_dict:
            return law_dict[num_part]

    return ""


def _lookup_in_db(section_number: str, law_type: str = "PPC") -> str:
    """Try to find a section in the database. Returns title or empty string."""
    try:
        from app.core.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT english_title FROM law_sections WHERE law_type = %s AND section_number = %s LIMIT 1",
            (law_type.upper(), section_number.strip()),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return row["english_title"]
    except Exception:
        pass  # DB not available or table not created yet — fall through to hardcoded
    return ""


def get_crime_name(section: str) -> tuple:
    """
    Get the English crime/offence name and law type for a section number.

    Checks the database first (if available), then falls back to the
    hardcoded dictionaries.

    Handles PPC sections (plain numbers like "302") and prefixed sections
    from other Pakistani criminal laws (e.g., "ATA-7", "CNSA-9", "ARMS-13").

    Args:
        section: Section string (e.g., "302", "ATA-7", "CNSA-9")

    Returns:
        tuple: (crime_name: str, law_type: str)
            - law_type is "PPC", "ATA", "CNSA", "Arms", etc.
            - crime_name is English description or "Unknown [Law] Section X"
    """
    import re
    section = str(section).strip()

    # Handle B-prefix sections (e.g., B-506 = Part B of Section 506 PPC)
    # These are NOT a separate law — they are Part B of the PPC section.
    b_prefix = re.match(r'^B[-\s]*(\d{2,3})$', section, re.IGNORECASE)
    if b_prefix:
        base_num = b_prefix.group(1)
        base_name, _ = get_crime_name(base_num)  # get the base section name
        part_b_description = f"{base_name} (Part B)"
        return (part_b_description, "PPC")

    # Check for prefixed sections (ATA-7, CNSA-9, ARMS-13, PECA-9, etc.)
    prefix_match = re.match(r'^([A-Za-z]+)[\s\-\.]+(.+)$', section)
    if prefix_match:
        prefix = prefix_match.group(1).upper()
        section_num = prefix_match.group(2).strip()

        # Try database first
        db_result = _lookup_in_db(section_num, prefix)
        if db_result:
            law_name = LAW_MAPPINGS.get(prefix, {}).get("name", prefix)
            return (db_result, law_name)

        if prefix in LAW_MAPPINGS:
            law_info = LAW_MAPPINGS[prefix]
            result = _lookup_in_dict(section_num, law_info["dict"])
            if result:
                return (result, law_info["name"])
            return (f"Unknown {law_info['name']} Section {section_num}", law_info["name"])

    # Try database first for PPC
    db_result = _lookup_in_db(section, "PPC")
    if db_result:
        return (db_result, "PPC")

    # Fallback to hardcoded PPC sections
    result = _lookup_in_dict(section, PPC_SECTIONS)
    if result:
        return (result, "PPC")

    return (f"Unknown PPC Section {section}", "PPC")


def get_ppc_simple_label(crime_name: str) -> str:
    """
    Derive a concise layman's label from a verbose PPC / law-section crime name.
    No hardcoded dictionary — uses pattern matching on the text itself.

    Examples:
        'Punishment for Murder'                        → 'Murder'
        'Punishment for Robbery'                       → 'Robbery'
        'Attempt to Commit Murder'                     → 'Attempted Murder'
        'Causing Death by Negligence'                  → 'Causing Death'
        'Acts Done by Several Persons in Furtherance…' → 'Acts Done by Several Persons'
    """
    import re
    name = crime_name.strip()

    # "Punishment for X" / "Penalty for X" / "Sentence for X" → X
    m = re.match(r'^(?:punishment|penalty|sentence|offence)\s+for\s+(.+)', name, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')

    # "Attempt to X" → "Attempted X"
    m = re.match(r'^attempt\s+to\s+(.+)', name, re.IGNORECASE)
    if m:
        return f"Attempted {m.group(1).strip().rstrip('.')}"

    # "Causing X by Y" / "Causing X" → "Causing X"
    m = re.match(r'^(causing\s+[\w\s]+?)(?:\s+by\s+.+)?$', name, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')

    # "X by Y" where X is 1–4 words → X
    m = re.match(r'^([\w][\w\s]{2,30})\s+by\s+.+', name, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')

    # Fallback: first 5 words
    words = name.split()
    return ' '.join(words[:5]).rstrip('.')


def get_crime_names(sections_list) -> list:
    """
    Get English crime/offence names for a list of section numbers.

    Handles both PPC sections and other Pakistani law sections (ATA, CNSA, etc.)

    Args:
        sections_list: List of section numbers (strings or ints)

    Returns:
        List of tuples: [(section_number, crime_name, law_type), ...]
    """
    results = []
    seen: set = set()
    for section in sections_list:
        s = str(section).strip()
        if s in seen:
            continue
        seen.add(s)
        crime_name, law_type = get_crime_name(s)
        results.append((s, crime_name, law_type))
    return results
