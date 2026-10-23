"""English and German vocabulary used by the parser and matchers.

Everything here is plain data. Words may be written with umlauts; they are folded
('Käse' -> 'kase') when loaded, so 'Käse', 'kase' and 'kaese' all work.
Pizza and ingredient names refer to the names in the recipe database. Entries for
names that are not in the database are ignored.
"""

# Words that carry no meaning for picking a pizza. Removed before matching.
STOPWORDS_EN = """
i id im ive ill d m s t ll ve me my mine we us our you your a an the one some any
please pls plz would like love want wanna need needs could can may might get got have has
had take order ordering give gimme bring make do does just maybe perhaps think guess go
with for to of is it its that this these those there be will let lets ok okay yes yeah
yep sure hi hello hey thanks thank cheers good great nice then so also and or but plus
pizza pizzas pie pies style kind type sort large small medium big regular normal classic
hungry today tonight now really very much lot something what how about instead rather
prefer again another too same usual delicious tasty yummy fresh please hmm uh um well
order on top out off
"""

STOPWORDS_DE = """
ich mir mich mein meine wir uns du dir ihr sie es man ein eine einen einem einer eins
der die das den dem des bitte gern gerne mochte mochten moechte moechten hatte hatten
haette haetten haben hab habe nehme nehmen nimm will wollen wurde wurden wuerde wuerden
gib geben bestellen bestelle bestellung mal doch ja jo hallo hi hey servus moin danke
dank und oder mit fur fuer zu von vom auf als noch dann also vielleicht lieber eher so
pizza pizzen sorte art gross grosse grossen kleine klein mittel heute jetzt bekomme
bekommen krieg kriegen kann konnte koennte hunger was einmal nochmal normale normal
klassische klassisch leckere lecker frische bitteschon gerade aber lass lassen drauf
"""

# Italian connectors that appear inside pizza names ('Salami e Funghi', 'Frutti di Mare').
STOPWORDS_IT = "e di del della con al alla"

# "Margherita WITHOUT basil": everything after the marker (until a terminator) is excluded.
EXCLUSION_PREFIX = """
without no hold minus except excluding leave remove skip sans
ohne kein keine keinen keinem keiner keines ausser nix
"""

# "Hawaii, Ananas WEGLASSEN": the words right before the marker are excluded.
EXCLUSION_POSTFIX = "weglassen weg raus"

# Words that end an exclusion list: "no onions ON my Tonno", "ohne Zwiebeln, ABER ...".
EXCLUSION_TERMINATORS = "on onto for fur fuer but aber with mit please bitte instead stattdessen"

# Words that separate items in an exclusion list: "without onions AND olives".
LIST_SEPARATORS = "and und or oder nor noch plus sowie also"

# Clause boundaries used to find where a postfix exclusion starts.
CLAUSE_BOUNDARIES = "aber but und and"

YES_WORDS = "yes yeah yep yup sure ok okay correct right exactly please ja jo jep klar genau gerne gern richtig passt stimmt"
NO_WORDS = "no nope nah none neither nein ne nee keine keiner nichts nothing nicht"
GREETING_WORDS = "hi hello hey hallo servus moin gruezi gruss gruß tag morning evening abend"
ALTERNATIVE_WORDS = "or oder either entweder"
CANCEL_WORDS = "cancel abort stop reset restart abbrechen abbruch neustart"
MENU_WORDS = "menu menue karte speisekarte options auswahl angebot list liste choices"
MENU_PHRASES = [
    "what do you have", "what pizzas", "which pizzas", "what can i order", "what is there",
    "was gibt es", "was habt ihr", "was haben sie", "welche pizzen", "welche pizza gibt es",
]
ORDINALS = {
    "1": 0, "first": 0, "erste": 0, "ersten": 0, "erstes": 0,
    "2": 1, "second": 1, "zweite": 1, "zweiten": 1, "zweites": 1,
    "3": 2, "third": 2, "dritte": 2, "dritten": 2, "drittes": 2,
    "4": 3, "fourth": 3, "vierte": 3, "vierten": 3, "viertes": 3,
    "5": 4, "fifth": 4, "funfte": 4, "fuenfte": 4,
}

# Words that hint at the language of a message.
GERMAN_HINTS = """
ich mochte moechte bitte ohne kein keine keinen und mit eine einen gerne gern hatte
haette hallo danke nehme die der das ja nein oder aber lieber welche was gibt es
speisekarte karte zwiebeln schinken pilze kase kaese weglassen bestellen pizzen
"""
ENGLISH_HINTS = """
i want would like please without no and with the a an hi hello thanks yes onions ham
mushrooms cheese menu what have which or but instead order hold
"""

# Extra names for pizzas, keyed by the pizza's name in the database.
PIZZA_ALIASES = {
    "Pizza Margherita": ["margarita", "margharita", "margerita"],
    "Pizza Quattro Stagioni": ["four seasons", "4 seasons", "vier jahreszeiten", "4 jahreszeiten"],
    "Pizza Quattro Formaggi": [
        "four cheese", "four cheeses", "4 cheese", "4 cheeses",
        "vier käse", "4 käse", "käsepizza", "vier käsesorten",
    ],
    "Pizza Hawaii": ["hawaiian", "hawai", "ham pineapple", "schinken ananas"],
    "Pizza Tonno": ["tuna", "thunfisch", "tuna onion"],
    "Pizza Funghi": ["mushroom", "mushrooms", "pilze", "pilz", "champignon", "champignons", "fungi"],
    "Pizza Prosciutto": ["ham", "schinken", "prosciutto cotto"],
    "Pizza Prosciutto e Funghi": [
        "ham mushroom", "ham mushrooms", "schinken pilze", "schinken champignons",
    ],
    "Pizza Salami": ["salame"],
    "Pizza Salami e Funghi": [
        "salami mushroom", "salami mushrooms", "salami pilze", "salami champignons",
    ],
    "Pizza Diavola": ["diavolo", "devil", "spicy salami", "hot salami", "scharfe salami", "teufel"],
    "Pizza Frutti di Mare": ["seafood", "meeresfrüchte", "meeresfruchte"],
    "Pizza Gamberetti": ["shrimp", "shrimps", "prawn", "prawns", "garnelen", "krabben"],
    "Pizza Salmone": ["salmon", "lachs"],
    "Pizza Spinaci": ["spinach", "spinat"],
    "Pizza Vegetariana": [
        "vegetarian", "veggie", "vegetarisch", "vegetarische", "gemüse", "vegetable", "vegetables",
    ],
    "Veggie Supreme Pizza": ["veggie supreme", "vegetarian supreme"],
    "Pizza Patate": ["potato", "potatoes", "kartoffel", "kartoffeln"],
    "Pizza Bianca": ["white", "weiße", "weisse"],
    "Pizza Greek": ["greek", "griechisch", "griechische"],
    "Pizza Döner": ["doener", "kebab", "kebap", "döner kebab"],
    "Pizza Gyros": ["gyro"],
    "Pizza Chicken": ["hähnchen", "haehnchen", "hühnchen", "huehnchen", "huhn"],
    "BBQ Chicken Pizza": ["barbecue chicken", "bbq", "barbecue", "bbq hähnchen", "bbq huhn"],
    "Buffalo Chicken Pizza": ["buffalo", "buffalo wings"],
    "Meat Lovers Pizza": ["meat lover", "meatlovers", "meat", "fleisch", "fleischliebhaber"],
    "Supreme Pizza": ["supreme"],
    "Chicago Deep Dish": ["deep dish", "chicago"],
    "New York Cheese Pizza": ["new york", "ny", "nyc", "new york style", "cheese"],
    "Pizza Gorgonzola e Pere": ["gorgonzola pear", "gorgonzola birne"],
    "Pizza Goat Cheese & Honey": ["goat cheese", "ziegenkäse", "ziegenkäse honig"],
    "Pizza Prosciutto Crudo e Rucola": [
        "prosciutto crudo", "parma", "parma ham", "parmaschinken", "parmaschinken rucola",
    ],
    "Pizza Bismarck": ["bismark"],
    "Pizza Calzone": ["folded", "zugeklappt", "zugeklappte"],
    "Pizza Napoletana": ["napoli", "neapolitan", "neapolitanisch", "neapolitanische", "napolitana"],
    "Pizza Siciliana": ["sicilian", "sizilianisch", "sizilianische"],
    "Pizza Salsiccia": ["sausage", "italian sausage"],
    "Pizza Sucuk": ["sujuk", "sucuk"],
    "Pizza Calabrese": ["nduja", "calabrian", "kalabrisch"],
    "Pizza Pugliese": ["apulian"],
    "Pizza Mexicana": ["mexican", "mexikanisch", "mexikanische", "mexico"],
    "Pizza Bufala": ["buffalo mozzarella", "büffelmozzarella", "mozzarella di bufala"],
    "Pizza Pepperoni": ["peperoni"],
}

# Ingredient name in the database -> (German display name, extra English/German synonyms).
INGREDIENTS = {
    "Tomato Sauce": ("Tomatensoße", ["tomatensauce", "tomatensoße", "red sauce", "sugo", "passata", "tomato base"]),
    "Cream": ("Sahne", ["sahne", "rahm", "schmand", "creme fraiche", "crème fraîche", "cream sauce"]),
    "BBQ Sauce": ("BBQ-Soße", ["barbecue sauce", "bbq soße", "bbq sauce"]),
    "Buffalo Sauce": ("Buffalo-Soße", ["hot sauce", "buffalo soße"]),
    "Garlic Yogurt Sauce": ("Knoblauch-Joghurt-Soße", [
        "garlic sauce", "yogurt sauce", "yoghurt sauce", "knoblauchsoße", "knoblauchsauce",
        "joghurtsoße", "joghurtsauce", "weiße soße", "white sauce",
    ]),
    "Tzatziki": ("Tsatsiki", ["tsatsiki", "zaziki", "zatziki"]),
    "Pesto": ("Pesto", ["basil pesto", "basilikumpesto"]),
    "Mozzarella": ("Mozzarella", ["mozarella", "mozza"]),
    "Buffalo Mozzarella": ("Büffelmozzarella", ["bufala", "mozzarella di bufala", "büffelmozzarella"]),
    "Gorgonzola": ("Gorgonzola", []),
    "Parmesan": ("Parmesan", ["parmigiano", "parmigiano reggiano", "parmesankäse", "grana"]),
    "Fontina": ("Fontina", []),
    "Ricotta": ("Ricotta", []),
    "Blue Cheese": ("Blauschimmelkäse", ["bleu cheese", "blauschimmelkäse"]),
    "Feta": ("Feta", ["schafskäse", "hirtenkäse"]),
    "Goat Cheese": ("Ziegenkäse", ["goats cheese", "chevre", "ziegenkäse"]),
    "Salami": ("Salami", ["salame"]),
    "Spicy Salami": ("scharfe Salami", ["hot salami", "scharfe salami", "salami piccante"]),
    "Pepperoni": ("Pepperoni-Salami", ["pepperoni salami"]),
    "Cooked Ham": ("Kochschinken", ["kochschinken", "prosciutto cotto"]),
    "Prosciutto Crudo": ("Parmaschinken", ["parma ham", "parmaschinken", "rohschinken", "cured ham", "serrano"]),
    "Speck": ("Südtiroler Speck", ["südtiroler speck"]),
    "Italian Sausage": ("italienische Wurst", ["sausage", "salsiccia", "wurst", "italienische wurst"]),
    "Bacon": ("Bacon", ["frühstücksspeck", "baconstreifen"]),
    "Ground Beef": ("Hackfleisch", ["minced beef", "mince", "beef", "hackfleisch", "hack", "rinderhack"]),
    "Chicken": ("Hähnchen", ["hähnchen", "haehnchen", "huhn", "hühnchen", "hendl", "poulet", "hähnchenbrust"]),
    "Döner Meat": ("Dönerfleisch", ["döner", "doener", "kebab", "kebab meat", "dönerfleisch"]),
    "Gyros": ("Gyros", ["gyro"]),
    "Sucuk": ("Sucuk", ["sujuk"]),
    "Nduja": ("Nduja", ["'nduja"]),
    "Tuna": ("Thunfisch", ["thunfisch", "tonno"]),
    "Anchovies": ("Sardellen", ["anchovy", "sardellen", "sardelle", "anchovis"]),
    "Mussels": ("Miesmuscheln", ["mussel", "miesmuscheln"]),
    "Clams": ("Venusmuscheln", ["clam", "venusmuscheln", "vongole"]),
    "Shrimp": ("Garnelen", ["shrimps", "prawns", "prawn", "garnelen", "garnele", "krabben", "scampi", "gamberetti"]),
    "Squid": ("Tintenfisch", ["calamari", "calamares", "tintenfisch", "kalmar"]),
    "Smoked Salmon": ("Räucherlachs", ["salmon", "lachs", "räucherlachs"]),
    "Mushrooms": ("Champignons", ["mushroom", "champignons", "champignon", "pilze", "pilz", "funghi", "schwammerl"]),
    "Artichokes": ("Artischocken", ["artichoke", "artischocken", "artischocke", "carciofi"]),
    "Black Olives": ("schwarze Oliven", ["olives", "olive", "oliven", "schwarze oliven"]),
    "Onion": ("Zwiebeln", ["white onion", "white onions"]),
    "Red Onion": ("rote Zwiebeln", ["red onions", "rote zwiebel", "rote zwiebeln"]),
    "Bell Peppers": ("Paprika", ["bell pepper", "pepper", "peppers", "paprika", "paprikaschoten", "capsicum"]),
    "Zucchini": ("Zucchini", ["courgette", "courgettes", "zucchine"]),
    "Eggplant": ("Aubergine", ["aubergine", "auberginen", "melanzane"]),
    "Spinach": ("Spinat", ["spinat", "spinaci"]),
    "Garlic": ("Knoblauch", ["knoblauch", "aglio", "knofi"]),
    "Arugula": ("Rucola", ["rocket", "rucola", "rauke"]),
    "Cherry Tomatoes": ("Kirschtomaten", ["cherry tomato", "kirschtomaten", "cocktailtomaten"]),
    "Tomato Slices": ("Tomatenscheiben", ["sliced tomatoes", "fresh tomatoes", "tomatenscheiben", "frische tomaten"]),
    "Jalapeños": ("Jalapeños", ["jalapeno"]),
    "Chili Peppers": ("Chili", ["chili", "chilli", "chilis", "chillies", "chilies", "peperoni", "peperoncini", "peperoncino", "pepperoncini"]),
    "Corn": ("Mais", ["sweetcorn", "sweet corn", "mais"]),
    "Kidney Beans": ("Kidneybohnen", ["beans", "bohnen", "kidneybohnen"]),
    "Potatoes": ("Kartoffeln", ["potato", "kartoffeln", "kartoffel", "patate"]),
    "Capers": ("Kapern", ["kapern", "capperi"]),
    "Celery": ("Sellerie", ["sellerie", "staudensellerie"]),
    "Pineapple": ("Ananas", ["ananas"]),
    "Walnuts": ("Walnüsse", ["walnut", "walnüsse"]),
    "Pear": ("Birne", ["pears", "birne", "birnen"]),
    "Basil": ("Basilikum", ["basilikum", "basilico"]),
    "Oregano": ("Oregano", ["origano"]),
    "Rosemary": ("Rosmarin", ["rosmarin"]),
    "Parsley": ("Petersilie", ["petersilie", "prezzemolo"]),
    "Cilantro": ("Koriander", ["coriander", "koriander"]),
    "Dill": ("Dill", []),
    "Olive Oil": ("Olivenöl", ["oil", "olivenöl", "öl"]),
    "Sea Salt": ("Meersalz", ["salt", "salz", "meersalz"]),
    "Black Pepper": ("schwarzer Pfeffer", ["pfeffer", "schwarzer pfeffer"]),
    "Egg": ("Ei", ["eggs", "ei", "eier", "spiegelei"]),
    "Honey": ("Honig", ["honig"]),
}

# Words that stand for several ingredients at once: "no onions" removes both kinds of onion.
INGREDIENT_GROUPS = {
    "onion": ["Onion", "Red Onion"], "onions": ["Onion", "Red Onion"],
    "zwiebel": ["Onion", "Red Onion"], "zwiebeln": ["Onion", "Red Onion"],
    "cipolla": ["Onion", "Red Onion"], "cipolle": ["Onion", "Red Onion"],
    "ham": ["Cooked Ham", "Prosciutto Crudo"], "schinken": ["Cooked Ham", "Prosciutto Crudo"],
    "prosciutto": ["Cooked Ham", "Prosciutto Crudo"],
    "speck": ["Speck", "Bacon"],
    "salami": ["Salami", "Spicy Salami"],
    "tomato": ["Tomato Sauce", "Cherry Tomatoes", "Tomato Slices"],
    "tomatoes": ["Tomato Sauce", "Cherry Tomatoes", "Tomato Slices"],
    "tomate": ["Tomato Sauce", "Cherry Tomatoes", "Tomato Slices"],
    "tomaten": ["Tomato Sauce", "Cherry Tomatoes", "Tomato Slices"],
    "muscheln": ["Mussels", "Clams"], "shellfish": ["Mussels", "Clams", "Shrimp"],
    "schalentiere": ["Mussels", "Clams", "Shrimp"],
    "nuts": ["Walnuts"], "nüsse": ["Walnuts"], "nuesse": ["Walnuts"],
    "jalapenos": ["Jalapeños"],
    "spicy": ["Spicy Salami", "Chili Peppers", "Jalapeños", "Nduja", "Buffalo Sauce"],
    "scharf": ["Spicy Salami", "Chili Peppers", "Jalapeños", "Nduja", "Buffalo Sauce"],
    "scharfes": ["Spicy Salami", "Chili Peppers", "Jalapeños", "Nduja", "Buffalo Sauce"],
}

# Words that stand for a whole ingredient category from the database.
CATEGORY_WORDS = {
    "cheese": "cheese", "cheeses": "cheese", "käse": "cheese",
    "meat": "meat", "fleisch": "meat",
    "fish": "seafood", "seafood": "seafood", "fisch": "seafood",
    "meeresfrüchte": "seafood", "meeresfruechte": "seafood",
    "vegetables": "vegetable", "veggies": "vegetable", "veg": "vegetable",
    "gemüse": "vegetable", "gemuese": "vegetable",
    "herbs": "herb", "kräuter": "herb", "kraeuter": "herb",
    "sauce": "sauce", "soße": "sauce", "sosse": "sauce", "sose": "sauce",
}
