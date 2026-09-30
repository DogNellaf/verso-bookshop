"""Russian, French and German versions of the demo catalog.

Keyed by the English title from ``seed.BOOKS``. Each entry is
``(title, author, description)``.
"""

TRANSLATIONS: dict[str, dict[str, tuple[str, str, str]]] = {
    "The Great Gatsby": {
        "ru": (
            "Великий Гэтсби",
            "Ф. Скотт Фицджеральд",
            "Лето 1922 года. Таинственный миллионер Джей Гэтсби одержим Дэйзи "
            "Бьюкенен — сверкающий и трагический портрет американской мечты.",
        ),
        "fr": (
            "Gatsby le Magnifique",
            "F. Scott Fitzgerald",
            "Été 1922 : le mystérieux millionnaire Jay Gatsby et son obsession pour "
            "Daisy Buchanan — un portrait éblouissant et tragique du rêve américain.",
        ),
        "de": (
            "Der große Gatsby",
            "F. Scott Fitzgerald",
            "Sommer 1922: Der geheimnisvolle Millionär Jay Gatsby und seine Besessenheit "
            "von Daisy Buchanan — ein schillerndes, tragisches Porträt des amerikanischen Traums.",
        ),
    },
    "To Kill a Mockingbird": {
        "ru": (
            "Убить пересмешника",
            "Харпер Ли",
            "Пулитцеровский роман о расовой несправедливости на американском Юге "
            "глазами юной Глазастика, чей отец защищает несправедливо обвинённого.",
        ),
        "fr": (
            "Ne tirez pas sur l'oiseau moqueur",
            "Harper Lee",
            "Prix Pulitzer, ce roman raconte l'injustice raciale dans le Sud à travers "
            "les yeux de la jeune Scout, dont le père défend un homme accusé à tort.",
        ),
        "de": (
            "Wer die Nachtigall stört",
            "Harper Lee",
            "Der mit dem Pulitzerpreis ausgezeichnete Roman über Rassenungerechtigkeit im "
            "Süden der USA — erzählt von der jungen Scout, deren Vater einen zu Unrecht "
            "Angeklagten verteidigt.",
        ),
    },
    "1984": {
        "ru": (
            "1984",
            "Джордж Оруэлл",
            "Леденящая антиутопия, где слежка, пропаганда и тотальный контроль "
            "пронизывают каждый миг. Большой Брат следит за тобой — и свобода "
            "становится самой опасной мыслью.",
        ),
        "fr": (
            "1984",
            "George Orwell",
            "Une dystopie glaçante où surveillance, propagande et contrôle total "
            "régissent chaque instant. Big Brother vous regarde — et la liberté est "
            "l'idée la plus dangereuse de toutes.",
        ),
        "de": (
            "1984",
            "George Orwell",
            "Eine beklemmende Dystopie, in der Überwachung, Propaganda und totale "
            "Kontrolle jeden Moment bestimmen. Der Große Bruder sieht dich — und "
            "Freiheit ist der gefährlichste Gedanke von allen.",
        ),
    },
    "Brave New World": {
        "ru": (
            "О дивный новый мир",
            "Олдос Хаксли",
            "Будущее, созданное ради счастья, стабильности и удовольствия, — ценой "
            "свободы, искусства и правды. Пророческое видение общества, променявшего "
            "душу на комфорт.",
        ),
        "fr": (
            "Le Meilleur des mondes",
            "Aldous Huxley",
            "Un futur conçu pour le bonheur, la stabilité et le plaisir — au prix de la "
            "liberté, de l'art et de la vérité. La vision prophétique d'une société qui "
            "troque son âme contre le confort.",
        ),
        "de": (
            "Schöne neue Welt",
            "Aldous Huxley",
            "Eine Zukunft, geschaffen für Glück, Stabilität und Vergnügen — um den Preis "
            "von Freiheit, Kunst und Wahrheit. Huxleys prophetische Vision einer "
            "Gesellschaft, die ihre Seele gegen Komfort eintauscht.",
        ),
    },
    "The Catcher in the Rye": {
        "ru": (
            "Над пропастью во ржи",
            "Дж. Д. Сэлинджер",
            "Беспокойные, смешные и щемящие скитания Холдена Колфилда по Нью-Йорку "
            "после исключения из школы — голос целого поколения.",
        ),
        "fr": (
            "L'Attrape-cœurs",
            "J. D. Salinger",
            "L'errance agitée, drôle et bouleversante de Holden Caulfield dans New York "
            "après son renvoi du lycée — la voix de toute une génération.",
        ),
        "de": (
            "Der Fänger im Roggen",
            "J. D. Salinger",
            "Holden Caulfields rastlose, komische und herzzerreißende Streifzüge durch "
            "New York nach dem Rauswurf aus dem Internat — die Stimme einer Generation.",
        ),
    },
    "Pride and Prejudice": {
        "ru": (
            "Гордость и предубеждение",
            "Джейн Остин",
            "Остроумная Элизабет Беннет и гордый мистер Дарси учатся видеть друг друга "
            "без предубеждений. Самый любимый роман о любви, сословиях и первом "
            "впечатлении.",
        ),
        "fr": (
            "Orgueil et Préjugés",
            "Jane Austen",
            "La vive Elizabeth Bennet et le fier Mr Darcy apprennent à dépasser leurs "
            "préjugés. La comédie de mœurs la plus aimée sur l'amour, le rang et les "
            "premières impressions.",
        ),
        "de": (
            "Stolz und Vorurteil",
            "Jane Austen",
            "Die schlagfertige Elizabeth Bennet und der stolze Mr Darcy lernen, ihre "
            "Vorurteile zu überwinden. Die beliebteste Gesellschaftskomödie über Liebe, "
            "Stand und erste Eindrücke.",
        ),
    },
    "Crime and Punishment": {
        "ru": (
            "Преступление и наказание",
            "Фёдор Достоевский",
            "Нищий студент убивает старуху-процентщицу и тонет в вине и страхе. "
            "Великая психологическая драма о совести, страдании и искуплении.",
        ),
        "fr": (
            "Crime et Châtiment",
            "Fiodor Dostoïevski",
            "Un étudiant sans le sou assassine une vieille usurière et sombre dans la "
            "culpabilité et la paranoïa. Un immense drame psychologique sur la "
            "conscience, la souffrance et la rédemption.",
        ),
        "de": (
            "Schuld und Sühne",
            "Fjodor Dostojewski",
            "Ein mittelloser Student ermordet eine Pfandleiherin und wird von Schuld und "
            "Verfolgungswahn verzehrt. Ein gewaltiges psychologisches Drama über "
            "Gewissen, Leid und Erlösung.",
        ),
    },
    "The Hobbit": {
        "ru": (
            "Хоббит, или Туда и обратно",
            "Дж. Р. Р. Толкин",
            "Бильбо Бэггинс покидает уютную нору ради похода за сокровищем, которое "
            "стережёт дракон Смауг. Любимая всеми прелюдия к «Властелину колец».",
        ),
        "fr": (
            "Le Hobbit",
            "J. R. R. Tolkien",
            "Bilbo Sacquet quitte son confortable trou de hobbit pour une quête épique : "
            "reprendre un trésor gardé par le dragon Smaug. Le prélude adoré du "
            "Seigneur des Anneaux.",
        ),
        "de": (
            "Der Hobbit",
            "J. R. R. Tolkien",
            "Bilbo Beutlin wird aus seiner gemütlichen Hobbithöhle in ein Abenteuer "
            "gerissen: einen Schatz zurückzuerobern, den der Drache Smaug bewacht. Das "
            "geliebte Vorspiel zum Herrn der Ringe.",
        ),
    },
    "Fahrenheit 451": {
        "ru": (
            "451° по Фаренгейту",
            "Рэй Брэдбери",
            "В мире, где книги запрещены, а «пожарные» сжигают каждую найденную, "
            "один из них начинает сомневаться во всём. Пылающее предупреждение о "
            "цензуре и конформизме.",
        ),
        "fr": (
            "Fahrenheit 451",
            "Ray Bradbury",
            "Dans un monde où les livres sont interdits et où les « pompiers » les "
            "brûlent, l'un d'eux se met à tout remettre en question. Un avertissement "
            "ardent contre la censure et le conformisme.",
        ),
        "de": (
            "Fahrenheit 451",
            "Ray Bradbury",
            "In einer Welt, in der Bücher verboten sind und „Feuerwehrmänner“ jedes "
            "gefundene verbrennen, beginnt einer von ihnen alles zu hinterfragen. "
            "Bradburys flammende Warnung vor Zensur und Konformismus.",
        ),
    },
    "Animal Farm": {
        "ru": (
            "Скотный двор",
            "Джордж Оруэлл",
            "Животные восстают против хозяина-человека и обнаруживают, что власть "
            "развращает абсолютно. Беспощадная притча о преданной революции.",
        ),
        "fr": (
            "La Ferme des animaux",
            "George Orwell",
            "Les animaux se révoltent contre leur maître humain, pour découvrir que le "
            "pouvoir corrompt absolument. Une fable acérée sur la révolution trahie.",
        ),
        "de": (
            "Farm der Tiere",
            "George Orwell",
            "Die Tiere erheben sich gegen ihren menschlichen Herrn — und erfahren, dass "
            "Macht absolut korrumpiert. Eine messerscharfe Fabel über die verratene "
            "Revolution.",
        ),
    },
    "Jane Eyre": {
        "ru": (
            "Джейн Эйр",
            "Шарлотта Бронте",
            "Гувернантка-сирота влюбляется в мрачного мистера Рочестера, но Торнфилд "
            "хранит страшную тайну. Страстная, романтичная и незабываемая героиня.",
        ),
        "fr": (
            "Jane Eyre",
            "Charlotte Brontë",
            "Une gouvernante orpheline s'éprend de son sombre employeur, Mr Rochester — "
            "mais Thornfield Hall cache un terrible secret. Une héroïne farouche, "
            "romantique et inoubliable.",
        ),
        "de": (
            "Jane Eyre",
            "Charlotte Brontë",
            "Eine verwaiste Gouvernante verliebt sich in ihren grüblerischen Dienstherrn "
            "Mr Rochester — doch Thornfield Hall birgt ein schreckliches Geheimnis. Eine "
            "leidenschaftliche, unvergessliche Heldin.",
        ),
    },
    "Frankenstein": {
        "ru": (
            "Франкенштейн",
            "Мэри Шелли",
            "Виктор Франкенштейн создаёт жизнь — и развязывает трагедию честолюбия, "
            "одиночества и мести. Роман, с которого началась научная фантастика.",
        ),
        "fr": (
            "Frankenstein",
            "Mary Shelley",
            "Victor Frankenstein crée la vie — et déclenche une tragédie d'ambition, "
            "d'abandon et de vengeance. Le roman qui a donné naissance à la "
            "science-fiction.",
        ),
        "de": (
            "Frankenstein",
            "Mary Shelley",
            "Victor Frankenstein erschafft Leben — und entfesselt eine Tragödie aus "
            "Ehrgeiz, Verlassenheit und Rache. Der Roman, mit dem die Science-Fiction "
            "begann.",
        ),
    },
    "Moby-Dick": {
        "ru": (
            "Моби Дик",
            "Герман Мелвилл",
            "Одержимая охота капитана Ахава на белого кита, отнявшего у него ногу, "
            "ведёт «Пекод» и команду к катастрофе. Огромный, странный и захватывающий "
            "американский эпос.",
        ),
        "fr": (
            "Moby Dick",
            "Herman Melville",
            "La traque obsessionnelle du cachalot blanc par le capitaine Achab mène le "
            "Pequod et son équipage à la catastrophe. Une épopée américaine vaste, "
            "étrange et saisissante.",
        ),
        "de": (
            "Moby-Dick",
            "Herman Melville",
            "Kapitän Ahabs besessene Jagd auf den weißen Wal, der ihm ein Bein nahm, "
            "treibt die Pequod und ihre Mannschaft in die Katastrophe. Ein gewaltiges, "
            "fesselndes amerikanisches Epos.",
        ),
    },
    "Wuthering Heights": {
        "ru": (
            "Грозовой перевал",
            "Эмили Бронте",
            "На диких йоркширских пустошах обречённая страсть Хитклиффа и Кэтрин "
            "Эрншо отзывается в двух поколениях. Мрачный, завораживающий и "
            "неповторимый роман.",
        ),
        "fr": (
            "Les Hauts de Hurlevent",
            "Emily Brontë",
            "Sur les landes sauvages du Yorkshire, la passion maudite de Heathcliff et "
            "Catherine Earnshaw résonne sur deux générations. Sombre, obsédant et "
            "profondément original.",
        ),
        "de": (
            "Sturmhöhe",
            "Emily Brontë",
            "Im wilden Moor von Yorkshire hallt die verhängnisvolle Leidenschaft von "
            "Heathcliff und Catherine Earnshaw über zwei Generationen nach. Düster, "
            "betörend und einzigartig.",
        ),
    },
    "Dracula": {
        "ru": (
            "Дракула",
            "Брэм Стокер",
            "Письма и дневники рассказывают о поездке Джонатана Харкера в Трансильванию "
            "и о древнем графе, который последовал за ним в Англию. Главный роман о "
            "вампирах.",
        ),
        "fr": (
            "Dracula",
            "Bram Stoker",
            "À travers lettres et journaux intimes, le voyage de Jonathan Harker en "
            "Transylvanie et l'antique comte qui le suit jusqu'en Angleterre. Le roman "
            "de vampires par excellence.",
        ),
        "de": (
            "Dracula",
            "Bram Stoker",
            "In Briefen und Tagebüchern erzählt: Jonathan Harkers Reise nach "
            "Transsilvanien und der uralte Graf, der ihm nach England folgt. Der "
            "Vampirroman schlechthin.",
        ),
    },
    "Lord of the Flies": {
        "ru": (
            "Повелитель мух",
            "Уильям Голдинг",
            "Оказавшись на необитаемом острове, школьники пытаются управлять собой — "
            "и скатываются к дикости. Захватывающая притча о тьме внутри человека.",
        ),
        "fr": (
            "Sa Majesté des mouches",
            "William Golding",
            "Échoués sur une île déserte, des écoliers tentent de se gouverner — et "
            "sombrent dans la sauvagerie. Une parabole saisissante sur les ténèbres "
            "intérieures.",
        ),
        "de": (
            "Herr der Fliegen",
            "William Golding",
            "Auf einer einsamen Insel gestrandet, versuchen Schuljungen, sich selbst zu "
            "regieren — und verfallen der Barbarei. Eine packende Parabel über die "
            "Dunkelheit im Menschen.",
        ),
    },
    "The Picture of Dorian Gray": {
        "ru": (
            "Портрет Дориана Грея",
            "Оскар Уайльд",
            "Прекрасный юноша остаётся вечно молодым, а его портрет хранит следы "
            "каждого греха. Остроумная, декадентская и жуткая история о тщеславии и "
            "падении.",
        ),
        "fr": (
            "Le Portrait de Dorian Gray",
            "Oscar Wilde",
            "Un beau jeune homme reste éternellement jeune tandis que son portrait "
            "porte la trace de chaque péché. Le récit spirituel, décadent et glaçant "
            "de la vanité et de la corruption.",
        ),
        "de": (
            "Das Bildnis des Dorian Gray",
            "Oscar Wilde",
            "Ein schöner junger Mann bleibt ewig jung, während sein Porträt jede Sünde "
            "festhält. Wildes geistreiche, dekadente und schaurige Geschichte über "
            "Eitelkeit und Verderbnis.",
        ),
    },
    "The Old Man and the Sea": {
        "ru": (
            "Старик и море",
            "Эрнест Хемингуэй",
            "Старый кубинский рыбак сражается с гигантским марлином далеко в "
            "Гольфстриме. Скупая и светлая повесть о стойкости и достоинстве в "
            "поражении.",
        ),
        "fr": (
            "Le Vieil Homme et la Mer",
            "Ernest Hemingway",
            "Un vieux pêcheur cubain affronte un marlin géant au large, dans le Gulf "
            "Stream. Un récit dépouillé et lumineux sur l'endurance et la dignité dans "
            "la défaite.",
        ),
        "de": (
            "Der alte Mann und das Meer",
            "Ernest Hemingway",
            "Ein alter kubanischer Fischer kämpft weit draußen im Golfstrom mit einem "
            "riesigen Marlin. Eine karge, leuchtende Erzählung über Ausdauer und Würde "
            "in der Niederlage.",
        ),
    },
}
