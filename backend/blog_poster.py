"""
blog_poster.py — SEO blog generator for The Matcha Tee (90-topic queue)
Pulls real products + images, fills SEO templates, uploads to Shopify.
Zero AI API cost.

Usage:
  python blog_poster.py --list            show all topics + posted status
  python blog_poster.py                   post the NEXT unposted topic
  python blog_poster.py --topic 3 7 12   post specific topic IDs
  python blog_poster.py --batch 3        post next N unposted topics
  python blog_poster.py --all            post ALL remaining topics
"""
import os, sys, re, time, random, argparse, httpx
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
DOMAIN = "https://thematchatee.com"
BLOG_ID = 91457585265   # Style Guide blog

# ─── 90-Topic Queue ──────────────────────────────────────────────────────────
# product_kw: list of lowercase strings that match product titles
# template:   fan_roundup | celebrity_tshirt | gift_guide | lifestyle
TOPICS = [
    # ── Already posted (1-25) ──────────────────────────────────────────────
    {"id":1,"title":"Best 9-1-1 Gifts: Eddie Diaz & Evan Buckley Fan T-Shirts","seo_title":"Best 9-1-1 T-Shirts & Gifts: Eddie Diaz & Evan Buckley","meta":"Shop vintage-style 9-1-1 fan merch featuring Eddie Diaz and Evan Buckley. Graphic tees and hoodies with free UK shipping.","tags":"9-1-1, Eddie Diaz, Evan Buckley, TV show gifts, fan merch, graphic tees","product_kw":["eddie diaz","evan buckley"],"show":"9-1-1","subject":"Eddie Diaz and Evan Buckley","fandom_desc":"Fox's hit emergency drama 9-1-1","char_desc":"the fan-favourite firefighters from Station 118","why_love":"their brotherhood, emotional storylines, and undeniable chemistry","template":"fan_roundup"},
    {"id":2,"title":"Best Mr Darcy Gifts for Jane Austen & Pride and Prejudice Fans","seo_title":"Best Mr Darcy T-Shirts & Gifts for Jane Austen Fans","meta":"Find the perfect Pride and Prejudice gift. Shop Fitzwilliam Darcy vintage graphic tees and hoodies with free UK shipping.","tags":"Mr Darcy, Pride and Prejudice, Jane Austen, Fitzwilliam Darcy, book gifts, fan merch","product_kw":["fitzwilliam darcy","darcy"],"show":"Pride and Prejudice","subject":"Fitzwilliam Darcy","fandom_desc":"Jane Austen's beloved classic Pride and Prejudice","char_desc":"literature's most swoon-worthy hero","why_love":"his brooding charm, dry wit, and that lake scene","template":"fan_roundup"},
    {"id":3,"title":"Best Gossip Girl Gifts: Blair Waldorf & Serena van der Woodsen Merch","seo_title":"Best Gossip Girl T-Shirts: Blair Waldorf & Serena Gifts","meta":"Shop vintage-style Gossip Girl fan merch. Blair Waldorf and Serena van der Woodsen graphic tees with free UK shipping.","tags":"Gossip Girl, Blair Waldorf, Serena, Upper East Side, TV show gifts, fan merch","product_kw":["blair waldorf","serena van woodsen"],"show":"Gossip Girl","subject":"Blair Waldorf and Serena van der Woodsen","fandom_desc":"the iconic CW drama Gossip Girl","char_desc":"the queen bees of the Upper East Side","why_love":"their fashion, their rivalry, and their complicated friendship","template":"fan_roundup"},
    {"id":4,"title":"Best Vampire Diaries Gifts: Damon Salvatore Fan T-Shirts & Merch","seo_title":"Best Vampire Diaries T-Shirts: Damon Salvatore Fan Gifts","meta":"Shop vintage-style Vampire Diaries fan merch. Damon Salvatore and Salvatore Brothers graphic tees with free UK shipping.","tags":"Vampire Diaries, Damon Salvatore, Salvatore Brothers, TV show gifts, fan merch","product_kw":["damon salvatore","salvatore"],"show":"The Vampire Diaries","subject":"Damon Salvatore","fandom_desc":"the smash-hit supernatural drama The Vampire Diaries","char_desc":"the brooding, wickedly charming elder Salvatore brother","why_love":"his sharp one-liners, moral ambiguity, and undeniable style","template":"fan_roundup"},
    {"id":5,"title":"Best Leonardo DiCaprio T-Shirts: Vintage Retro Leo Fan Merch","seo_title":"Best Leonardo DiCaprio T-Shirts & Retro Fan Merch","meta":"Shop vintage-style Leonardo DiCaprio graphic tees and hoodies. Retro bootleg Leo merch with free UK shipping.","tags":"Leonardo DiCaprio, Leo, vintage celebrity, retro t-shirt, film fan gifts","product_kw":["leonardo dicaprio"],"show":"Hollywood","subject":"Leonardo DiCaprio","fandom_desc":"one of the greatest actors in Hollywood history","char_desc":"the Oscar-winning star of Titanic, The Revenant, and countless classics","why_love":"his unmatched range, iconic roles, and timeless 90s era","template":"celebrity_tshirt"},
    {"id":6,"title":"Princess Diana T-Shirts & Royal Family Fan Gifts","seo_title":"Best Princess Diana T-Shirts & Royal Family Fan Merch","meta":"Shop vintage-style Princess Diana and Royal Family graphic tees. Tribute merch for royal fans with free UK shipping.","tags":"Princess Diana, Royal Family, Queen Elizabeth, Prince Harry, Meghan Markle, tribute merch","product_kw":["princess diana","diana","queen elizabeth","prince harry","meghan markle"],"show":"The Royal Family","subject":"Princess Diana and the Royal Family","fandom_desc":"the most famous royal family in the world","char_desc":"the people's princess and the figures who shaped modern Britain","why_love":"her compassion, her style, and her enduring legacy","template":"celebrity_tshirt"},
    {"id":7,"title":"Best TWICE Merch: K-Pop T-Shirts & Gifts for ONCE Fans","seo_title":"Best TWICE K-Pop T-Shirts & ONCE Fan Gifts","meta":"Shop vintage-style TWICE K-pop merch. Jihyo, Momo, Tzuyu, and Chaeyoung graphic tees with free UK shipping.","tags":"TWICE, K-Pop, ONCE, Jihyo, Momo, Tzuyu, Chaeyoung, K-pop merch","product_kw":["jihyo","momo","tzuyu","chaeyoung","twice"],"show":"TWICE","subject":"TWICE","fandom_desc":"JYP Entertainment's record-breaking K-pop girl group","char_desc":"Jihyo, Momo, Tzuyu, Chaeyoung and the whole TWICE lineup","why_love":"their addictive discography, incredible performances, and warm fan connection","template":"fan_roundup"},
    {"id":8,"title":"Best K-Drama Fan Gifts: T-Shirts for Korean Drama Lovers","seo_title":"Best K-Drama T-Shirts & Fan Gifts for Korean Drama Fans","meta":"Shop vintage-style K-drama fan merch. Byeon Woo Seok, Cha Eunwoo, and more graphic tees with free UK shipping.","tags":"K-Drama, Korean drama, Byeon Woo Seok, Cha Eunwoo, Kim Go-Eun, Lee Dohyun, fan gifts","product_kw":["byeon woo seok","cha eunwoo","kim go-eun","lee dohyun","lee dongwook","han so-hee"],"show":"K-Drama","subject":"the biggest K-drama stars","fandom_desc":"the world of Korean drama","char_desc":"the hottest actors lighting up Netflix and beyond","why_love":"their captivating performances, beautiful aesthetics, and addictive storylines","template":"fan_roundup"},
    {"id":9,"title":"Best Breaking Bad & Better Call Saul Gifts: Lalo Salamanca Fan Merch","seo_title":"Best Breaking Bad Gifts: Lalo Salamanca T-Shirts & Merch","meta":"Shop vintage-style Breaking Bad and Better Call Saul fan merch. Lalo Salamanca graphic tees with free UK shipping.","tags":"Breaking Bad, Better Call Saul, Lalo Salamanca, TV show gifts, fan merch","product_kw":["lalo salamanca","breaking bad"],"show":"Breaking Bad / Better Call Saul","subject":"Lalo Salamanca","fandom_desc":"the critically acclaimed Breaking Bad universe","char_desc":"the terrifyingly charming cartel boss from Better Call Saul","why_love":"his unpredictability, dark humour, and scene-stealing presence","template":"fan_roundup"},
    {"id":10,"title":"Best Classic Hollywood T-Shirts: Retro Actor Merch & Vintage Tees","seo_title":"Best Classic Hollywood T-Shirts: Retro Vintage Actor Merch","meta":"Shop vintage-style classic Hollywood graphic tees. Al Pacino, Johnny Depp, Patrick Swayze and more with free UK shipping.","tags":"classic Hollywood, Al Pacino, Johnny Depp, Patrick Swayze, Tom Selleck, vintage celebrity tees","product_kw":["al pacino","johnny depp","patrick swayze","robert redford","tom selleck","ethan hawke"],"show":"Classic Hollywood","subject":"the legends of classic Hollywood","fandom_desc":"the golden age of Hollywood cinema","char_desc":"the timeless icons of Al Pacino, Johnny Depp, Patrick Swayze, and Robert Redford","why_love":"their iconic performances, cool-beyond-measure screen presence, and cultural impact","template":"celebrity_tshirt"},
    {"id":11,"title":"Best Music Icon T-Shirts: Vintage Artist & Band Fan Tees","seo_title":"Best Music Icon T-Shirts: Vintage Artist & Band Merch","meta":"Shop vintage-style music fan tees. Courtney Love, Gwen Stefani, Ricky Martin, Vanilla Ice and more with free UK shipping.","tags":"music merch, Courtney Love, Gwen Stefani, Ricky Martin, Vanilla Ice, vintage band tees","product_kw":["courtney love","gwen stefani","ricky martin","vanilla ice","serj tankian","damiano david","rosalia","tom jones"],"show":"Music Icons","subject":"legendary music icons","fandom_desc":"the world of music icons past and present","char_desc":"the legendary artists who defined their era — from Courtney Love to Gwen Stefani","why_love":"their anthems, their attitude, and their unforgettable fashion","template":"celebrity_tshirt"},
    {"id":12,"title":"Best Grey's Anatomy Gifts: Derek Shepherd Fan T-Shirts & Merch","seo_title":"Best Grey's Anatomy T-Shirts & Gifts: Derek Shepherd Merch","meta":"Shop vintage-style Grey's Anatomy fan merch. Derek Shepherd graphic tees and hoodies with free UK shipping.","tags":"Grey's Anatomy, Derek Shepherd, McDreamy, TV show gifts, fan merch, medical drama","product_kw":["derek shepherd"],"show":"Grey's Anatomy","subject":"Derek Shepherd","fandom_desc":"the long-running ABC medical drama Grey's Anatomy","char_desc":"the beloved neurosurgeon and McDreamy himself","why_love":"his gentle strength, his love for Meredith, and that devastating storyline","template":"fan_roundup"},
    {"id":13,"title":"Best Stranger Things Cast T-Shirts: Finn Wolfhard & Jamie Campbell Bower Merch","seo_title":"Best Stranger Things Cast T-Shirts: Finn Wolfhard Fan Merch","meta":"Shop vintage-style Stranger Things cast tees. Finn Wolfhard and Jamie Campbell Bower graphic tees with free UK shipping.","tags":"Stranger Things, Finn Wolfhard, Jamie Campbell Bower, Netflix, TV show gifts, fan merch","product_kw":["finn wolfhard","jamie campbell"],"show":"Stranger Things","subject":"Finn Wolfhard and Jamie Campbell Bower","fandom_desc":"Netflix's smash-hit supernatural drama Stranger Things","char_desc":"the stars behind Mike Wheeler and the terrifying Vecna","why_love":"their incredible performances in Hawkins and beyond","template":"fan_roundup"},
    {"id":14,"title":"Best David Attenborough Gifts for Nature & Wildlife Lovers","seo_title":"Best David Attenborough T-Shirts & Gifts for Nature Fans","meta":"Shop vintage-style David Attenborough graphic tees. Perfect gifts for nature and wildlife lovers with free UK shipping.","tags":"David Attenborough, wildlife, nature fan gifts, BBC, documentary, graphic tee","product_kw":["david attenborough"],"show":"Sir David Attenborough","subject":"Sir David Attenborough","fandom_desc":"Britain's most beloved broadcaster and naturalist","char_desc":"the voice of the natural world and national treasure","why_love":"his calm wisdom, his passion for the planet, and his extraordinary legacy","template":"celebrity_tshirt"},
    {"id":15,"title":"Best Stephen King Gifts for Horror Fans: T-Shirts & Fan Merch","seo_title":"Best Stephen King T-Shirts & Gifts for Horror Fans","meta":"Shop vintage-style Stephen King graphic tees. Perfect gifts for horror and thriller fans with free UK shipping.","tags":"Stephen King, horror fan gifts, IT, The Shining, book fan, graphic tee","product_kw":["stephen king"],"show":"Stephen King","subject":"Stephen King","fandom_desc":"the master of horror and bestselling novelist","char_desc":"the author behind IT, The Shining, Misery, and over 60 novels","why_love":"his unmatched ability to terrify, his prolific output, and his iconic status","template":"celebrity_tshirt"},
    {"id":16,"title":"Best Boy Meets World Gifts: Mr Feeny Fan T-Shirts & Merch","seo_title":"Best Boy Meets World T-Shirts: Mr Feeny Fan Gifts","meta":"Shop vintage-style Boy Meets World fan merch. Mr Feeny graphic tees for 90s TV fans with free UK shipping.","tags":"Boy Meets World, Mr Feeny, 90s TV, nostalgia gifts, fan merch, graphic tees","product_kw":["mr feeny","feeny"],"show":"Boy Meets World","subject":"Mr Feeny","fandom_desc":"the beloved 90s sitcom Boy Meets World","char_desc":"the wise teacher and neighbour who shaped a generation","why_love":"his life lessons, his endless patience, and that iconic 'Feeny call'","template":"fan_roundup"},
    {"id":17,"title":"Best Scandal TV Show Gifts: Fitzgerald Grant Fan Merch","seo_title":"Best Scandal T-Shirts & Gifts: Fitzgerald Grant Fan Merch","meta":"Shop vintage-style Scandal fan merch. Fitzgerald Grant graphic tees for political drama fans with free UK shipping.","tags":"Scandal, Fitzgerald Grant, Olivia Pope, political drama, TV show gifts, fan merch","product_kw":["fitzgerald grant","scandal"],"show":"Scandal","subject":"Fitzgerald Grant","fandom_desc":"the gripping ABC political thriller Scandal","char_desc":"the complicated, charismatic President of the United States","why_love":"the intense drama, the power plays, and his electrifying dynamic with Olivia Pope","template":"fan_roundup"},
    {"id":18,"title":"Napoleon Bonaparte T-Shirts: History Fan Gifts & Vintage Merch","seo_title":"Best Napoleon Bonaparte T-Shirts & History Fan Gifts","meta":"Shop vintage-style Napoleon Bonaparte graphic tees. Unique history fan gifts with free UK shipping.","tags":"Napoleon Bonaparte, history fan gifts, French history, vintage merch, graphic tees","product_kw":["napoleon"],"show":"History","subject":"Napoleon Bonaparte","fandom_desc":"the history of one of the world's most captivating military leaders","char_desc":"the Emperor of France and military genius whose legacy spans centuries","why_love":"his ambition, his tactical brilliance, and his complicated legacy","template":"celebrity_tshirt"},
    {"id":19,"title":"Best Jenna Marbles Merch: YouTube Creator Fan T-Shirts","seo_title":"Best Jenna Marbles T-Shirts & YouTube Creator Fan Merch","meta":"Shop vintage-style Jenna Marbles graphic tees. YouTube creator fan merch with free UK shipping.","tags":"Jenna Marbles, YouTube, creator merch, fan gifts, graphic tees, internet culture","product_kw":["jenna marbles"],"show":"YouTube","subject":"Jenna Marbles","fandom_desc":"the pioneering YouTube creator Jenna Mourey, known as Jenna Marbles","char_desc":"the beloved internet personality who built one of YouTube's biggest communities","why_love":"her authentic humour, her genuine care for fans, and her iconic videos","template":"celebrity_tshirt"},
    {"id":20,"title":"Best The Santa Clause Gifts: Scott Calvin & Tim Allen Fan Merch","seo_title":"Best The Santa Clause T-Shirts & Scott Calvin Fan Gifts","meta":"Shop vintage-style The Santa Clause fan merch. Scott Calvin and Tim Allen graphic tees with free UK shipping.","tags":"The Santa Clause, Scott Calvin, Tim Allen, Christmas gifts, holiday merch, 90s film","product_kw":["scott calvin","tim allen"],"show":"The Santa Clause","subject":"Scott Calvin / Tim Allen","fandom_desc":"the beloved 90s holiday classic The Santa Clause","char_desc":"the accidental Santa himself, Scott Calvin","why_love":"the warm nostalgia, the Christmas magic, and Tim Allen at his best","template":"fan_roundup"},
    {"id":21,"title":"Christmas Gift Ideas for TV Show Fans: Graphic Tees & Fan Merch","seo_title":"Christmas Gift Ideas for TV Show Fans 2026 | The Matcha Tee","meta":"Stuck for Christmas gift ideas? Shop vintage graphic tees for fans of 9-1-1, Gossip Girl, Grey's Anatomy and more. Free UK shipping.","tags":"Christmas gifts, TV show fans, fan merch, graphic tees, gift ideas 2026","product_kw":["eddie diaz","blair waldorf","derek shepherd","damon salvatore","fitzwilliam darcy"],"show":"TV Shows","subject":"your favourite TV show characters","fandom_desc":"the best of TV drama, past and present","char_desc":"characters from 9-1-1, Gossip Girl, Grey's Anatomy, Vampire Diaries and more","why_love":"the drama, the characters, and the storylines we can't stop talking about","template":"gift_guide"},
    {"id":22,"title":"Best Birthday Gift Ideas for Film & TV Fans: Vintage Graphic Tees","seo_title":"Best Birthday Gifts for Film & TV Fans: Graphic Tees","meta":"Find the perfect birthday gift for a film or TV fan. Vintage graphic tees and hoodies for every fandom with free UK shipping.","tags":"birthday gifts, film fan, TV fan, graphic tees, fan merch, gift ideas","product_kw":["leonardo dicaprio","al pacino","johnny depp","evan buckley","blair waldorf"],"show":"Film & TV","subject":"your favourite film and TV icons","fandom_desc":"the world of film and television","char_desc":"legends from Hollywood, prestige TV, and everything in between","why_love":"the stories, the performances, and the cultural moments they created","template":"gift_guide"},
    {"id":23,"title":"Best Gifts for K-Pop Fans: TWICE & K-Drama Star Merch","seo_title":"Best K-Pop Gifts: TWICE & K-Drama Fan T-Shirts","meta":"Shop the best K-pop and K-drama fan gifts. TWICE, Byeon Woo Seok, Cha Eunwoo and more graphic tees with free UK shipping.","tags":"K-pop gifts, K-drama, TWICE, Byeon Woo Seok, Cha Eunwoo, Korean fan merch","product_kw":["jihyo","momo","tzuyu","chaeyoung","byeon woo seok","cha eunwoo","kim go-eun","lee dohyun"],"show":"K-Pop & K-Drama","subject":"the biggest names in K-pop and K-drama","fandom_desc":"the global phenomenon of K-pop and Korean drama","char_desc":"TWICE, Byeon Woo Seok, Cha Eunwoo and the stars of Korean entertainment","why_love":"the music, the fashion, the storytelling, and the passionate fanbase","template":"gift_guide"},
    {"id":24,"title":"Best Gifts for Her: Vintage Celebrity T-Shirts She'll Actually Wear","seo_title":"Best Gifts for Her: Vintage Celebrity T-Shirts & Fan Merch","meta":"The perfect gift for her — vintage celebrity graphic tees she'll love wearing. Princess Diana, Gossip Girl, Pride & Prejudice and more. Free UK shipping.","tags":"gifts for her, celebrity t-shirts, Princess Diana, Blair Waldorf, Mr Darcy, women's fan merch","product_kw":["princess diana","blair waldorf","fitzwilliam darcy","serena van woodsen","meghan markle"],"show":"Pop Culture","subject":"pop culture icons she'll love","fandom_desc":"the most beloved women's culture icons","char_desc":"Princess Diana, Blair Waldorf, Fitzwilliam Darcy and more iconic figures","why_love":"their style, their strength, and their lasting cultural impact","template":"gift_guide"},
    {"id":25,"title":"Best Gifts for 90s Kids: Nostalgia T-Shirts & Retro Fan Merch","seo_title":"Best 90s Nostalgia T-Shirts & Gifts for 90s Kids","meta":"Shop the best 90s nostalgia graphic tees. Vanilla Ice, Gwen Stefani, Boy Meets World, Jenna Marbles and more with free UK shipping.","tags":"90s nostalgia, 90s gifts, vintage t-shirts, retro merch, 90s TV, 90s music","product_kw":["vanilla ice","gwen stefani","mr feeny","jenna marbles","ricky martin","courtney love"],"show":"the 90s","subject":"90s icons","fandom_desc":"the decade that shaped a generation","char_desc":"Vanilla Ice, Gwen Stefani, Mr Feeny, and the icons of the 90s","why_love":"the music, the fashion, the TV shows, and the pure unfiltered nostalgia","template":"gift_guide"},

    # ── New topics (26-90) ─────────────────────────────────────────────────

    # Product-specific: remaining characters/celebrities
    {"id":26,"title":"Best Addison Rae Fan T-Shirts: TikTok Star & Actress Merch","seo_title":"Best Addison Rae T-Shirts & Fan Merch | The Matcha Tee","meta":"Shop vintage-style Addison Rae graphic tees. The perfect gift for fans of the TikTok star turned actress. Free UK shipping.","tags":"Addison Rae, TikTok, social media star, fan merch, graphic tees, pop culture","product_kw":["addison rae"],"show":"Social Media / Pop Culture","subject":"Addison Rae","fandom_desc":"TikTok's most followed creator turned pop star and actress","char_desc":"the Louisiana-born content creator who became a Gen Z icon","why_love":"her energy, her authenticity, and her rapid rise from TikTok to Hollywood","template":"celebrity_tshirt"},
    {"id":27,"title":"Best Austin Butler T-Shirts: Elvis & Dune Fan Merch","seo_title":"Best Austin Butler T-Shirts: Elvis & Dune Fan Merch","meta":"Shop vintage-style Austin Butler graphic tees. From Elvis to Dune — retro fan merch with free UK shipping.","tags":"Austin Butler, Elvis, Dune, Feyd-Rautha, fan merch, vintage celebrity tee","product_kw":["austin butler"],"show":"Austin Butler's Career","subject":"Austin Butler","fandom_desc":"one of Hollywood's most exciting young actors","char_desc":"the star who transformed himself for Baz Luhrmann's Elvis and terrified audiences as Feyd-Rautha in Dune","why_love":"his total commitment to every role, his versatility, and that Elvis performance that blew everyone away","template":"celebrity_tshirt"},
    {"id":28,"title":"Best Balki Bartokomous T-Shirts: Perfect Strangers Fan Gifts","seo_title":"Best Perfect Strangers T-Shirts: Balki Bartokomous Fan Merch","meta":"Shop vintage-style Balki Bartokomous and Perfect Strangers graphic tees. 80s sitcom nostalgia gifts with free UK shipping.","tags":"Perfect Strangers, Balki Bartokomous, 80s TV, sitcom nostalgia, fan merch, retro tee","product_kw":["balki"],"show":"Perfect Strangers","subject":"Balki Bartokomous","fandom_desc":"the beloved 80s ABC sitcom Perfect Strangers","char_desc":"the loveable Myposian immigrant whose friendship with Cousin Larry became TV comedy gold","why_love":"his wide-eyed optimism, his hilarious malapropisms, and the sheer warmth of the show","template":"fan_roundup"},
    {"id":29,"title":"Best Bernie Mac Fan T-Shirts: Comedy Legend Tribute Merch","seo_title":"Best Bernie Mac T-Shirts: Comedy Legend Fan Tribute Merch","meta":"Shop vintage-style Bernie Mac tribute graphic tees. Celebrate a comedy legend with free UK shipping.","tags":"Bernie Mac, comedy legend, stand-up, The Bernie Mac Show, tribute merch, vintage tee","product_kw":["bernie mac"],"show":"The Bernie Mac Show / Stand-Up Comedy","subject":"Bernie Mac","fandom_desc":"one of the greatest stand-up comedians and sitcom stars of his generation","char_desc":"the Chicago-born comedian whose fearless style and The Bernie Mac Show made him a legend","why_love":"his fearless honesty, his unmatched stage presence, and his heartfelt comedy","template":"celebrity_tshirt"},
    {"id":30,"title":"Best Big Ocean Fan T-Shirts: Country Music Fan Merch","seo_title":"Best Big Ocean T-Shirts & Country Music Fan Gifts","meta":"Shop vintage-style Big Ocean graphic tees. Country pop fan merch for The Voice fans with free UK shipping.","tags":"Big Ocean, country music, The Voice, fan merch, graphic tees, country pop","product_kw":["big ocean"],"show":"The Voice / Country Music","subject":"Big Ocean","fandom_desc":"the Utah-based country pop band who captured hearts on The Voice","char_desc":"the brother-and-sister duo known for their heartfelt harmonies and feel-good sound","why_love":"their genuine connection with fans, their tight harmonies, and their uplifting music","template":"celebrity_tshirt"},
    {"id":31,"title":"Best Brendan Fraser Fan T-Shirts: The Comeback Story Merch","seo_title":"Best Brendan Fraser T-Shirts: Oscar Winner Fan Merch","meta":"Shop vintage-style Brendan Fraser graphic tees. Celebrate his incredible comeback with fan merch. Free UK shipping.","tags":"Brendan Fraser, The Whale, Oscar, comeback, 90s films, Mummy, fan merch","product_kw":["brendan fraser"],"show":"Brendan Fraser's Career","subject":"Brendan Fraser","fandom_desc":"the beloved 90s action star who made one of Hollywood's greatest comebacks","char_desc":"the star of The Mummy, Encino Man, and Oscar-winner for The Whale","why_love":"his warmth, his resilience, and the comeback that genuinely moved the entire internet","template":"celebrity_tshirt"},
    {"id":32,"title":"Best Da Vinci T-Shirts: Art & History Fan Gifts","seo_title":"Best Leonardo Da Vinci T-Shirts & Art Fan Gifts","meta":"Shop vintage-style Leonardo Da Vinci graphic tees. Unique gifts for art and history lovers with free UK shipping.","tags":"Da Vinci, Leonardo Da Vinci, art fan gifts, history, Renaissance, graphic tee","product_kw":["da vinci"],"show":"History & Art","subject":"Leonardo Da Vinci","fandom_desc":"the Renaissance genius whose art and inventions changed the world","char_desc":"the painter of the Mona Lisa and the Last Supper, and visionary inventor centuries ahead of his time","why_love":"his endless curiosity, his breathtaking artistry, and his timeless cultural impact","template":"celebrity_tshirt"},
    {"id":33,"title":"Best David Tennant Fan T-Shirts: Doctor Who & Good Omens Merch","seo_title":"Best David Tennant T-Shirts: Doctor Who & Good Omens Fan Gifts","meta":"Shop vintage-style David Tennant graphic tees. The perfect Doctor Who and Good Omens fan gift with free UK shipping.","tags":"David Tennant, Doctor Who, Good Omens, The Doctor, fan merch, British TV","product_kw":["david tennant"],"show":"Doctor Who / Good Omens","subject":"David Tennant","fandom_desc":"one of Britain's most beloved actors, known for Doctor Who, Good Omens and much more","char_desc":"the Tenth Doctor and Crowley himself — two of the most iconic roles in British television","why_love":"his electric energy, his emotional range, and his ability to make every character unforgettable","template":"celebrity_tshirt"},
    {"id":34,"title":"Best Dewey Fan T-Shirts: Walk Hard & Pop Culture Merch","seo_title":"Best Dewey T-Shirts & Walk Hard Fan Gifts","meta":"Shop vintage-style Dewey graphic tees. Pop culture fan merch for fans of the iconic character with free UK shipping.","tags":"Dewey, Walk Hard, pop culture, cult comedy, fan merch, graphic tee","product_kw":["dewey"],"show":"Pop Culture","subject":"Dewey","fandom_desc":"the beloved pop culture character who became a cult icon","char_desc":"the loveable, chaotic character whose story resonates across generations of fans","why_love":"his commitment, his passion, and the humour packed into every scene","template":"celebrity_tshirt"},
    {"id":35,"title":"Best Ethan Hawke Fan T-Shirts: Indie Cinema & Before Trilogy Merch","seo_title":"Best Ethan Hawke T-Shirts: Indie Cinema Fan Merch","meta":"Shop vintage-style Ethan Hawke graphic tees. Perfect for fans of the Before Trilogy, Training Day and more. Free UK shipping.","tags":"Ethan Hawke, Before Sunrise, indie cinema, Training Day, fan merch, vintage celebrity tee","product_kw":["ethan hawke"],"show":"Indie Cinema","subject":"Ethan Hawke","fandom_desc":"one of indie cinema's most enduring and critically acclaimed actors","char_desc":"the star of Before Sunrise, Training Day, and Moon Knight — always unexpected, always compelling","why_love":"his intellectual depth, his commitment to challenging roles, and his quiet magnetic screen presence","template":"celebrity_tshirt"},
    {"id":36,"title":"Best Evan Peters Fan T-Shirts: American Horror Story & Dahmer Merch","seo_title":"Best Evan Peters T-Shirts: AHS & Dahmer Fan Merch","meta":"Shop vintage-style Evan Peters graphic tees. Fan merch for AHS and Dahmer fans with free UK shipping.","tags":"Evan Peters, American Horror Story, Dahmer, Netflix, fan merch, graphic tees","product_kw":["evan peters"],"show":"American Horror Story / Dahmer","subject":"Evan Peters","fandom_desc":"Ryan Murphy's go-to star and one of the most fearless actors of his generation","char_desc":"the actor who brought serial killer Jeffrey Dahmer to life and terrorised AHS fans for over a decade","why_love":"his complete transformation in every role, his bravery as a performer, and his huge fan following","template":"celebrity_tshirt"},
    {"id":37,"title":"Best Jon Bernthal Fan T-Shirts: The Punisher & Walking Dead Merch","seo_title":"Best Jon Bernthal T-Shirts: Punisher & Walking Dead Fan Gifts","meta":"Shop vintage-style Jon Bernthal graphic tees. The Punisher and Walking Dead fan merch with free UK shipping.","tags":"Jon Bernthal, The Punisher, Walking Dead, Frank Castle, Shane Walsh, fan merch","product_kw":["jon bernthal"],"show":"The Punisher / The Walking Dead","subject":"Jon Bernthal","fandom_desc":"the intense, brooding actor known for The Punisher and The Walking Dead","char_desc":"Frank Castle himself — the most compelling Punisher Marvel has ever given us","why_love":"his raw intensity, his physical commitment to every role, and the pure menace he brings to the screen","template":"celebrity_tshirt"},
    {"id":38,"title":"Best Max Black T-Shirts: 2 Broke Girls Fan Merch & Gifts","seo_title":"Best Max Black T-Shirts & 2 Broke Girls Fan Gifts","meta":"Shop vintage-style Max Black and 2 Broke Girls graphic tees. Fan merch with free UK shipping.","tags":"Max Black, 2 Broke Girls, sitcom, fan merch, Kat Dennings, graphic tees","product_kw":["max black"],"show":"2 Broke Girls","subject":"Max Black","fandom_desc":"the hit CBS sitcom 2 Broke Girls","char_desc":"the sharp-tongued, sarcastic but big-hearted Max Black","why_love":"her razor-sharp wit, her loyalty to Caroline, and the way she made being broke feel kind of cool","template":"fan_roundup"},
    {"id":39,"title":"Best Meryl Streep Fan T-Shirts: Hollywood Legend Tribute Merch","seo_title":"Best Meryl Streep T-Shirts & Hollywood Legend Fan Gifts","meta":"Shop vintage-style Meryl Streep graphic tees. The perfect gift for fans of the greatest actress of all time. Free UK shipping.","tags":"Meryl Streep, Hollywood, actress, The Devil Wears Prada, Kramer vs Kramer, fan merch","product_kw":["meryl streep"],"show":"Hollywood / Cinema","subject":"Meryl Streep","fandom_desc":"the undisputed greatest actress in Hollywood history","char_desc":"the three-time Oscar winner behind The Devil Wears Prada, Sophie's Choice, Kramer vs. Kramer and dozens more","why_love":"her unparalleled range, her effortless accents, and the fact that she genuinely has no bad films","template":"celebrity_tshirt"},
    {"id":40,"title":"Best Mitchel Musso Fan T-Shirts: Hannah Montana & Disney Channel Nostalgia","seo_title":"Best Mitchel Musso T-Shirts: Disney Channel Nostalgia Fan Merch","meta":"Shop vintage-style Mitchel Musso graphic tees. Hannah Montana nostalgia merch with free UK shipping.","tags":"Mitchel Musso, Hannah Montana, Disney Channel, nostalgia, Oliver Oken, fan merch","product_kw":["mitchel musso"],"show":"Hannah Montana / Disney Channel","subject":"Mitchel Musso","fandom_desc":"the beloved Disney Channel era that defined a generation of TV","char_desc":"Oliver Oken himself from Hannah Montana — the loyal, loveable friend everyone wanted","why_love":"the pure Disney Channel nostalgia, the catchy songs, and the early 2000s vibes","template":"celebrity_tshirt"},
    {"id":41,"title":"Best Natalie Portman Fan T-Shirts: Black Swan & Star Wars Merch","seo_title":"Best Natalie Portman T-Shirts: Black Swan & Star Wars Fan Gifts","meta":"Shop vintage-style Natalie Portman graphic tees. From Black Swan to Star Wars — retro fan merch with free UK shipping.","tags":"Natalie Portman, Black Swan, Star Wars, Padme, fan merch, vintage celebrity tee","product_kw":["natalie portman"],"show":"Film / Cinema","subject":"Natalie Portman","fandom_desc":"one of the most respected and versatile actresses in Hollywood","char_desc":"the Oscar-winning star of Black Swan and Queen Padmé Amidala of the Star Wars prequels","why_love":"her intelligence, her Oscar-winning intensity in Black Swan, and her longevity as a Hollywood icon","template":"celebrity_tshirt"},
    {"id":42,"title":"Best Pauly Shore Fan T-Shirts: 90s Comedy Movies Nostalgia Merch","seo_title":"Best Pauly Shore T-Shirts: 90s Comedy Fan Merch","meta":"Shop vintage-style Pauly Shore graphic tees. 90s comedy nostalgia merch with free UK shipping.","tags":"Pauly Shore, Bio-Dome, Encino Man, 90s comedy, nostalgia, fan merch, retro tee","product_kw":["pauly shore"],"show":"90s Comedy Films","subject":"Pauly Shore","fandom_desc":"the comedic force behind Bio-Dome, Encino Man, and Son in Law","char_desc":"the Weasel himself — the quintessential 90s comedy man-child","why_love":"his manic energy, his totally unique comedy style, and the sheer nostalgia he carries","template":"celebrity_tshirt"},
    {"id":43,"title":"Best Rob Lowe T-Shirts: Parks and Recreation & Brat Pack Merch","seo_title":"Best Rob Lowe T-Shirts: Parks and Rec & Brat Pack Fan Gifts","meta":"Shop vintage-style Rob Lowe graphic tees. Parks and Recreation and 80s Brat Pack fan merch with free UK shipping.","tags":"Rob Lowe, Parks and Recreation, Chris Traeger, Brat Pack, St. Elmo's Fire, fan merch","product_kw":["rob lowe"],"show":"Parks and Recreation / Brat Pack Era","subject":"Rob Lowe","fandom_desc":"the multi-decade Hollywood icon from the Brat Pack to Parks and Recreation","char_desc":"the effortlessly charming star of St. Elmo's Fire and the relentlessly positive Chris Traeger","why_love":"his impeccable comic timing, his ageless looks, and the way he made Chris Traeger a fan favourite","template":"celebrity_tshirt"},
    {"id":44,"title":"Best Rod Kimble T-Shirts: Hot Rod Cult Classic Fan Merch","seo_title":"Best Rod Kimble T-Shirts: Hot Rod Fan Merch | The Matcha Tee","meta":"Shop vintage-style Rod Kimble and Hot Rod graphic tees. Cult comedy fan merch with free UK shipping.","tags":"Rod Kimble, Hot Rod, Andy Samberg, cult comedy, fan merch, graphic tees","product_kw":["rod kimble"],"show":"Hot Rod (2007)","subject":"Rod Kimble","fandom_desc":"the 2007 cult comedy classic Hot Rod starring Andy Samberg","char_desc":"Rod Kimble — the delusional but loveable stuntman trying to honour his dead father","why_love":"the absurdist humour, the committed performance, and the way it became a cult classic over the years","template":"fan_roundup"},
    {"id":45,"title":"Best Sasha Colby Fan T-Shirts: RuPaul's Drag Race Legend Merch","seo_title":"Best Sasha Colby T-Shirts & Drag Race Fan Merch","meta":"Shop vintage-style Sasha Colby graphic tees. RuPaul's Drag Race fan merch with free UK shipping.","tags":"Sasha Colby, RuPaul's Drag Race, drag queen, fan merch, LGBTQ+, graphic tees","product_kw":["sasha colby"],"show":"RuPaul's Drag Race All Stars","subject":"Sasha Colby","fandom_desc":"RuPaul's Drag Race All Stars 8, where Sasha Colby absolutely dominated","char_desc":"the drag legend, former Miss Continental, and Drag Race icon who set a new standard for the show","why_love":"her technical precision, her stunning looks, and the way she made every lip sync look effortless","template":"celebrity_tshirt"},
    {"id":46,"title":"Best Sebastian Stan Fan T-Shirts: Winter Soldier & The Apprentice Merch","seo_title":"Best Sebastian Stan T-Shirts: Winter Soldier Fan Merch","meta":"Shop vintage-style Sebastian Stan graphic tees. MCU and The Apprentice fan merch with free UK shipping.","tags":"Sebastian Stan, Bucky Barnes, Winter Soldier, MCU, The Apprentice, fan merch","product_kw":["sebastian stan"],"show":"MCU / The Apprentice","subject":"Sebastian Stan","fandom_desc":"the MCU's Winter Soldier and one of Hollywood's most magnetic leading men","char_desc":"Bucky Barnes himself — and the actor who stunned everyone as a young Donald Trump in The Apprentice","why_love":"his quiet intensity, his dedication to the role of Bucky across over a decade of films, and his incredible range","template":"celebrity_tshirt"},
    {"id":47,"title":"Best Skeet Ulrich Fan T-Shirts: Scream & Riverdale Merch","seo_title":"Best Skeet Ulrich T-Shirts: Scream & Riverdale Fan Gifts","meta":"Shop vintage-style Skeet Ulrich graphic tees. Scream and Riverdale fan merch with free UK shipping.","tags":"Skeet Ulrich, Scream, Billy Loomis, Riverdale, FP Jones, fan merch, horror","product_kw":["skeet ulrich"],"show":"Scream / Riverdale","subject":"Skeet Ulrich","fandom_desc":"the Scream franchise and Riverdale","char_desc":"Billy Loomis in Scream and FP Jones in Riverdale — a career built on compelling bad boys","why_love":"his brooding energy, his iconic role in the original Scream, and his Riverdale comeback","template":"celebrity_tshirt"},
    {"id":48,"title":"Best Sophie Thatcher Fan T-Shirts: Yellowjackets & Star Wars Merch","seo_title":"Best Sophie Thatcher T-Shirts: Yellowjackets & Boba Fett Fan Gifts","meta":"Shop vintage-style Sophie Thatcher graphic tees. Yellowjackets and Book of Boba Fett fan merch with free UK shipping.","tags":"Sophie Thatcher, Yellowjackets, Book of Boba Fett, The Boys, fan merch, graphic tees","product_kw":["sophie thatcher"],"show":"Yellowjackets / The Book of Boba Fett","subject":"Sophie Thatcher","fandom_desc":"one of TV's most exciting young actresses","char_desc":"Teen Natalie in Yellowjackets and Omega in The Book of Boba Fett — already building an incredible career","why_love":"her emotional depth, her ability to hold complex scenes, and her star-is-rising energy","template":"celebrity_tshirt"},
    {"id":49,"title":"Best Todd Chrisley Fan T-Shirts: Chrisley Knows Best Merch","seo_title":"Best Todd Chrisley T-Shirts: Chrisley Knows Best Fan Gifts","meta":"Shop vintage-style Todd Chrisley graphic tees. Reality TV fan merch with free UK shipping.","tags":"Todd Chrisley, Chrisley Knows Best, reality TV, fan merch, graphic tees","product_kw":["todd chrisley"],"show":"Chrisley Knows Best","subject":"Todd Chrisley","fandom_desc":"the hit USA Network reality show Chrisley Knows Best","char_desc":"the self-styled Southern patriarch whose one-liners made the show appointment TV","why_love":"his unfiltered opinions, his family dynamics, and his genuinely quotable commentary on life","template":"celebrity_tshirt"},
    {"id":50,"title":"Best Thomas Doherty Fan T-Shirts: Gossip Girl Reboot Merch","seo_title":"Best Thomas Doherty T-Shirts & Gossip Girl Reboot Fan Merch","meta":"Shop vintage-style Thomas Doherty graphic tees. Gossip Girl reboot fan merch with free UK shipping.","tags":"Thomas Doherty, Gossip Girl reboot, Max Wolfe, fan merch, British actor, graphic tees","product_kw":["thomas doherty"],"show":"Gossip Girl (2021 Reboot)","subject":"Thomas Doherty","fandom_desc":"the 2021 HBO Max Gossip Girl reboot","char_desc":"Max Wolfe himself — the charismatic, boundary-pushing character at the heart of the new Upper East Side","why_love":"his magnetic screen presence, his effortless cool, and the character who stole the whole show","template":"celebrity_tshirt"},
    {"id":51,"title":"Best Troy Bolton T-Shirts: High School Musical Nostalgia Merch","seo_title":"Best Troy Bolton T-Shirts: High School Musical Fan Merch","meta":"Shop vintage-style Troy Bolton and High School Musical graphic tees. 2000s Disney nostalgia with free UK shipping.","tags":"Troy Bolton, High School Musical, HSM, Zac Efron, Disney, nostalgia, fan merch","product_kw":["troy bolton"],"show":"High School Musical","subject":"Troy Bolton","fandom_desc":"Disney Channel's era-defining High School Musical franchise","char_desc":"the basketball captain who chose to sing — and made a whole generation believe they could do both","why_love":"the iconic songs, the pure 2000s nostalgia, and the way the whole franchise still holds up","template":"fan_roundup"},
    {"id":52,"title":"Best Young Sheldon Fan T-Shirts: Dr Sturgis Gifts & Merch","seo_title":"Best Young Sheldon T-Shirts: Dr Sturgis Fan Gifts","meta":"Shop vintage-style Young Sheldon and Dr Sturgis graphic tees. Fan merch with free UK shipping.","tags":"Young Sheldon, Dr Sturgis, Big Bang Theory, fan merch, science, sitcom gifts","product_kw":["dr. sturgis","sturgis"],"show":"Young Sheldon","subject":"Dr. John Sturgis","fandom_desc":"the CBS prequel sitcom Young Sheldon","char_desc":"the eccentric physicist and Meemaw's love interest who became a fan favourite","why_love":"his literal-minded charm, his unlikely romance arc, and the warmth he brought to the show","template":"fan_roundup"},
    {"id":53,"title":"Best Josh Shapiro Fan T-Shirts: Political Fan Merch","seo_title":"Best Josh Shapiro T-Shirts & Political Fan Merch","meta":"Shop vintage-style Josh Shapiro graphic tees. Political fan merch with free UK shipping.","tags":"Josh Shapiro, Pennsylvania Governor, political, fan merch, graphic tees","product_kw":["josh saphiro","shapiro"],"show":"US Politics","subject":"Josh Shapiro","fandom_desc":"Pennsylvania Governor and prominent figure in American politics","char_desc":"the two-term Attorney General turned Governor known for his sharp communications and no-nonsense style","why_love":"his directness, his track record, and the way he became a political figure fans genuinely rally around","template":"celebrity_tshirt"},
    {"id":54,"title":"Best Howard Han Fan T-Shirts: Pop Culture Fan Merch","seo_title":"Best Howard Han T-Shirts & Pop Culture Fan Merch","meta":"Shop vintage-style Howard Han graphic tees. Fan merch for pop culture enthusiasts with free UK shipping.","tags":"Howard Han, pop culture, fan merch, graphic tees, celebrity tee","product_kw":["howard han"],"show":"Pop Culture","subject":"Howard Han","fandom_desc":"the pop culture figure who built a dedicated fan following","char_desc":"a personality whose style and presence resonates with fans who love authentic storytelling","why_love":"their dedication to their craft and the genuine community they've built","template":"celebrity_tshirt"},

    # Trend-adjacent (shows/themes tied to products)
    {"id":55,"title":"Best American Horror Story Gifts: Evan Peters Fan T-Shirts","seo_title":"Best American Horror Story T-Shirts & Evan Peters Fan Gifts","meta":"Shop vintage-style AHS fan merch. Evan Peters graphic tees and hoodies with free UK shipping.","tags":"American Horror Story, AHS, Evan Peters, Ryan Murphy, horror fan gifts, fan merch","product_kw":["evan peters"],"show":"American Horror Story","subject":"Evan Peters in AHS","fandom_desc":"Ryan Murphy's genre-defining anthology horror series American Horror Story","char_desc":"Evan Peters, who played 11 different iconic characters across 9 seasons of the show","why_love":"the anthology format, the outrageous storytelling, and Evan Peters never giving a bad performance","template":"fan_roundup"},
    {"id":56,"title":"Best Elvis Fan T-Shirts: Austin Butler & Baz Luhrmann Tribute Merch","seo_title":"Best Elvis T-Shirts: Austin Butler Fan Gifts & Tribute Merch","meta":"Shop vintage-style Elvis and Austin Butler graphic tees. Perfect for fans of the Baz Luhrmann biopic. Free UK shipping.","tags":"Elvis, Austin Butler, Baz Luhrmann, Elvis Presley, fan merch, tribute tee, vintage celebrity","product_kw":["austin butler"],"show":"Elvis (2022) / Elvis Presley","subject":"Austin Butler's Elvis","fandom_desc":"Baz Luhrmann's spectacular 2022 biopic Elvis","char_desc":"Austin Butler's extraordinary, life-defining portrayal of the King of Rock and Roll","why_love":"the showmanship, the tragedy, and Austin Butler's total immersion in the role that earned him an Oscar nomination","template":"fan_roundup"},
    {"id":57,"title":"Best Titanic Fan Gifts: Jack Dawson & Leonardo DiCaprio Merch","seo_title":"Best Titanic Fan T-Shirts: Jack Dawson & Leo DiCaprio Gifts","meta":"Shop vintage-style Titanic fan merch. Jack Dawson and Leonardo DiCaprio graphic tees with free UK shipping.","tags":"Titanic, Jack Dawson, Leonardo DiCaprio, Rose, fan merch, classic film gifts, Kate Winslet","product_kw":["jack dawson","leonardo dicaprio"],"show":"Titanic (1997)","subject":"Jack Dawson and Leonardo DiCaprio","fandom_desc":"James Cameron's Titanic — one of the greatest films ever made","char_desc":"Jack Dawson, the free-spirited artist who stole Rose's heart and ours too","why_love":"the epic romance, the heartbreak, and Leo at the absolute peak of his 90s icon status","template":"fan_roundup"},
    {"id":58,"title":"Best Scream Fan T-Shirts: Skeet Ulrich & Horror Movie Merch","seo_title":"Best Scream T-Shirts: Skeet Ulrich & Horror Fan Gifts","meta":"Shop vintage-style Scream and horror fan merch. Skeet Ulrich graphic tees with free UK shipping.","tags":"Scream, Skeet Ulrich, Billy Loomis, horror fan, slasher, fan merch, Ghostface","product_kw":["skeet ulrich"],"show":"Scream (1996) Film Series","subject":"Skeet Ulrich in Scream","fandom_desc":"Wes Craven's genre-redefining Scream franchise","char_desc":"the original Ghostface killer, Billy Loomis — one of horror's most iconic villains","why_love":"the meta-horror brilliance, the twists, and the way Scream changed everything for horror films","template":"fan_roundup"},
    {"id":59,"title":"Best RuPaul's Drag Race Fan Gifts: Sasha Colby & Drag Culture Tees","seo_title":"Best Drag Race T-Shirts: Sasha Colby & LGBTQ+ Fan Gifts","meta":"Shop vintage-style RuPaul's Drag Race fan merch. Sasha Colby graphic tees with free UK shipping.","tags":"RuPaul's Drag Race, Sasha Colby, LGBTQ+, drag queen, fan gifts, All Stars","product_kw":["sasha colby"],"show":"RuPaul's Drag Race","subject":"the queens of RuPaul's Drag Race","fandom_desc":"the Emmy-winning cultural phenomenon that is RuPaul's Drag Race","char_desc":"the extraordinary queens who make every episode must-watch TV — with Sasha Colby leading the charge","why_love":"the creativity, the lip syncs, the drama, and the way it celebrates individuality every week","template":"fan_roundup"},
    {"id":60,"title":"Best Marvel & Punisher Fan T-Shirts: Jon Bernthal & Bucky Barnes Merch","seo_title":"Best Marvel Fan T-Shirts: Punisher & Winter Soldier Gifts","meta":"Shop vintage-style Marvel fan merch. Jon Bernthal and Sebastian Stan graphic tees with free UK shipping.","tags":"Marvel, The Punisher, Frank Castle, Bucky Barnes, Winter Soldier, Jon Bernthal, Sebastian Stan","product_kw":["jon bernthal","sebastian stan"],"show":"Marvel / The Punisher / The Falcon and the Winter Soldier","subject":"Jon Bernthal and Sebastian Stan's Marvel characters","fandom_desc":"the Netflix and Disney+ Marvel series featuring these two incredible actors","char_desc":"Frank Castle (The Punisher) and Bucky Barnes (The Winter Soldier) — two of Marvel's most complex characters","why_love":"the moral complexity, the action, and actors who genuinely elevate their superhero material","template":"fan_roundup"},
    {"id":61,"title":"Best High School Musical Fan Gifts: Troy Bolton Nostalgia Tees","seo_title":"Best High School Musical Gifts: Troy Bolton Fan Merch","meta":"Shop vintage-style High School Musical and Troy Bolton graphic tees. 2000s Disney nostalgia gifts with free UK shipping.","tags":"High School Musical, HSM, Troy Bolton, Zac Efron, Disney Channel, nostalgia gifts","product_kw":["troy bolton"],"show":"High School Musical","subject":"Troy Bolton and High School Musical","fandom_desc":"Disney Channel's iconic High School Musical franchise","char_desc":"the basketball-playing, show-stopping Troy Bolton who defined a generation of Disney Channel fans","why_love":"the songs you still know all the words to, the 2000s aesthetic, and the unbeatable nostalgia hit","template":"fan_roundup"},
    {"id":62,"title":"Best Doctor Who Fan Gifts: David Tennant T-Shirts & Time Lord Merch","seo_title":"Best Doctor Who T-Shirts: David Tennant Fan Gifts","meta":"Shop vintage-style Doctor Who and David Tennant graphic tees. Fan merch for Whovians with free UK shipping.","tags":"Doctor Who, David Tennant, Tenth Doctor, Whovian, BBC, fan merch, British TV","product_kw":["david tennant"],"show":"Doctor Who","subject":"David Tennant's Doctor","fandom_desc":"the BBC's iconic long-running sci-fi series Doctor Who","char_desc":"the Tenth Doctor — widely considered the greatest incarnation of the Time Lord ever","why_love":"the wit, the heartbreak, the adventures, and David Tennant's unique ability to make every emotion land","template":"fan_roundup"},

    # Gift occasions
    {"id":63,"title":"Mother's Day Gift Guide: Fan T-Shirts She'll Actually Wear","seo_title":"Mother's Day Gifts for Mums: Fan T-Shirts She'll Actually Wear","meta":"The best Mother's Day gifts for mums who love TV shows, films, and pop culture. Vintage graphic tees with free UK shipping.","tags":"Mother's Day gifts, gifts for mum, fan merch, graphic tees, Princess Diana, Pride and Prejudice","product_kw":["princess diana","fitzwilliam darcy","blair waldorf","meryl streep","natalie portman"],"show":"Pop Culture","subject":"the icons your mum actually loves","fandom_desc":"the films, shows, and figures your mum has always adored","char_desc":"Princess Diana, Meryl Streep, Fitzwilliam Darcy and the icons that defined her era","why_love":"their timeless style, emotional depth, and enduring cultural relevance","template":"gift_guide"},
    {"id":64,"title":"Father's Day Gift Ideas: Celebrity T-Shirts for Film-Loving Dads","seo_title":"Father's Day Gifts for Dads: Vintage Celebrity T-Shirts","meta":"The perfect Father's Day gift for film-loving dads. Classic Hollywood and sport celebrity tees with free UK shipping.","tags":"Father's Day gifts, gifts for dad, celebrity t-shirts, Al Pacino, Tom Selleck, Patrick Swayze","product_kw":["al pacino","tom selleck","patrick swayze","robert redford","ethan hawke","rob lowe"],"show":"Classic Film","subject":"the icons your dad grew up loving","fandom_desc":"the golden era of Hollywood film and television","char_desc":"Al Pacino, Tom Selleck, Patrick Swayze and the legends of the silver screen","why_love":"the films, the performances, and the cultural touchstones that defined a generation","template":"gift_guide"},
    {"id":65,"title":"Back to School Outfit Ideas: Vintage Graphic Tees for Students","seo_title":"Back to School Outfit Ideas: Vintage Graphic Tees for Students","meta":"Start the school year in style with vintage graphic tees. Pop culture fan tees for students with free UK shipping.","tags":"back to school, student fashion, graphic tees, vintage style, pop culture, outfit ideas","product_kw":["addison rae","austin butler","evan peters","finn wolfhard","sophie thatcher"],"show":"Youth Pop Culture","subject":"the icons today's students love","fandom_desc":"contemporary pop culture, from TikTok to prestige TV","char_desc":"Addison Rae, Austin Butler, Evan Peters and the faces of young Hollywood","why_love":"their cool factor, cultural relevance, and the way they represent exactly what's in right now","template":"gift_guide"},
    {"id":66,"title":"Gift Ideas for Teenagers: Pop Culture T-Shirts They'll Love","seo_title":"Gift Ideas for Teenagers: Pop Culture T-Shirts & Fan Merch","meta":"Find the perfect gift for a teenager. Pop culture graphic tees they'll actually be excited to wear. Free UK shipping.","tags":"gifts for teenagers, teen gifts, pop culture, fan merch, graphic tees, K-pop, Stranger Things","product_kw":["finn wolfhard","addison rae","austin butler","byeon woo seok","cha eunwoo","jihyo"],"show":"Youth Pop Culture","subject":"the icons teenagers actually care about","fandom_desc":"the world of TikTok, K-pop, and prestige TV that shapes teen culture today","char_desc":"Finn Wolfhard, Addison Rae, TWICE, and the faces teens actually follow","why_love":"their cultural relevance, their social media presence, and the way teens connect with them genuinely","template":"gift_guide"},
    {"id":67,"title":"Halloween Costume Ideas Using Graphic Tees: Easy Fan Merch Costumes","seo_title":"Halloween Costume Ideas Using Fan T-Shirts | The Matcha Tee","meta":"Easy Halloween costume ideas using graphic tees. Fan merch that doubles as a costume for TV and film characters. Free UK shipping.","tags":"Halloween costume ideas, graphic tee costumes, fan merch, Halloween gifts, Billy Loomis, Eddie Diaz","product_kw":["skeet ulrich","evan peters","damon salvatore","lalo salamanca","eddie diaz"],"show":"Halloween / Pop Culture","subject":"your favourite Halloween-ready characters","fandom_desc":"the world of horror and drama that makes for perfect Halloween costumes","char_desc":"Billy Loomis, Damon Salvatore, Lalo Salamanca and the characters perfect for a Halloween-themed tee","why_love":"the drama, the menace, and the way a great graphic tee is the easiest costume base ever","template":"gift_guide"},
    {"id":68,"title":"Christmas Stocking Fillers for TV & Film Fans Under £30","seo_title":"Christmas Stocking Fillers for TV Fans: Graphic Tees Under £30","meta":"The best Christmas stocking fillers for TV and film fans. Vintage graphic tees under £30 with free UK shipping.","tags":"stocking fillers, Christmas gifts, TV fans, under £30, graphic tees, fan merch","product_kw":["scott calvin","tim allen","mr feeny","max black","jenna marbles"],"show":"TV & Film","subject":"your favourite TV and film characters","fandom_desc":"the shows and characters that make Christmas TV-watching so special","char_desc":"Scott Calvin, Mr Feeny, Max Black and the characters that make the holiday season feel festive","why_love":"the warmth, the nostalgia, and the way certain shows just feel made for Christmas viewing","template":"gift_guide"},
    {"id":69,"title":"Secret Santa Gift Ideas Under £30: Fan T-Shirts for Every Fandom","seo_title":"Secret Santa Gift Ideas Under £30: Fan T-Shirts & Merch","meta":"The best Secret Santa gifts under £30 for any pop culture fan. Vintage graphic tees with free UK shipping.","tags":"Secret Santa, gifts under £30, fan merch, graphic tees, office gift, gift guide","product_kw":["david attenborough","stephen king","napoleon","da vinci","meryl streep"],"show":"Pop Culture / Film / TV","subject":"pop culture icons that make perfect Secret Santa gifts","fandom_desc":"the broad world of pop culture with something for every taste","char_desc":"from David Attenborough to Meryl Streep — icons that work for any Secret Santa","why_love":"their universal recognition, their cultural weight, and the way a good tee says 'I put thought into this'","template":"gift_guide"},
    {"id":70,"title":"Valentine's Day Gifts for Pop Culture Fans: Romantic Fan Merch","seo_title":"Valentine's Day Gifts for Pop Culture Fans | The Matcha Tee","meta":"The best Valentine's Day gifts for pop culture fans. Romantic fan tees and hoodies with free UK shipping.","tags":"Valentine's Day gifts, romantic fan merch, Mr Darcy, Jack Dawson, Titanic, Pride and Prejudice","product_kw":["fitzwilliam darcy","jack dawson","leonardo dicaprio","derek shepherd","damon salvatore"],"show":"Romance / Film & TV","subject":"the most romantic figures in pop culture","fandom_desc":"the films and shows that gave us the greatest love stories","char_desc":"Mr Darcy, Jack Dawson, and Derek Shepherd — the romantic icons fans never got over","why_love":"the swoon-worthy moments, the timeless declarations of love, and the characters we still wish existed","template":"gift_guide"},
    {"id":71,"title":"Graduation Gift Ideas: Vintage Fan T-Shirts They'll Actually Wear","seo_title":"Graduation Gift Ideas: Vintage Graphic Tees for New Graduates","meta":"Find the perfect graduation gift. Vintage fan tees that celebrate pop culture and individual style. Free UK shipping.","tags":"graduation gifts, graduate gift ideas, fan merch, graphic tees, pop culture","product_kw":["rob lowe","natalie portman","ethan hawke","meryl streep","austin butler"],"show":"Film & Pop Culture","subject":"icons who inspire the next generation","fandom_desc":"the figures who prove talent, hard work, and authenticity always win","char_desc":"Natalie Portman, Ethan Hawke, and the achievers who built incredible careers from nothing","why_love":"their dedication, their artistry, and the inspiration they bring to anyone starting a new chapter","template":"gift_guide"},

    # Lifestyle / style content
    {"id":72,"title":"How to Style a Vintage Celebrity T-Shirt: 2026 Outfit Ideas","seo_title":"How to Style a Vintage Celebrity T-Shirt: 2026 Style Guide","meta":"Learn how to style vintage celebrity and fan graphic tees for any occasion. Outfit ideas and style tips. Free UK shipping.","tags":"how to style graphic tees, vintage celebrity tee, outfit ideas, fashion tips, fan merch styling","product_kw":["princess diana","fitzwilliam darcy","leonardo dicaprio","blair waldorf","evan peters"],"show":"Fashion / Style","subject":"vintage celebrity graphic tees","fandom_desc":"the world of vintage bootleg-style fashion","char_desc":"our full collection of graphic tees and hoodies","why_love":"their versatility, their character, and the way a great graphic tee elevates any casual outfit","template":"lifestyle"},
    {"id":73,"title":"Why Bootleg Fan Merch Is Back in Fashion in 2026","seo_title":"Why Bootleg Fan Merch Is Trending Again in 2026","meta":"The bootleg tee revival explained — why vintage-style fan merch is everywhere right now and how to wear it. Free UK shipping.","tags":"bootleg tee, vintage fan merch, fashion trends 2026, graphic tee revival, pop culture fashion","product_kw":["courtney love","vanilla ice","jenna marbles","austin butler","evan peters"],"show":"Fashion Trends","subject":"the bootleg tee revival","fandom_desc":"the resurgence of vintage-style fan merchandise","char_desc":"the icons whose bootleg tees are most in demand right now","why_love":"the authenticity, the nostalgia, and the way they blend fan culture with genuine fashion sense","template":"lifestyle"},
    {"id":74,"title":"What to Wear to a Watch Party: Graphic Tee Outfit Ideas","seo_title":"Watch Party Outfit Ideas: The Best Graphic Tees to Wear","meta":"Planning a watch party? Wear a graphic tee that shows off your fandom. Outfit ideas and styling tips. Free UK shipping.","tags":"watch party outfit, graphic tee, fan merch, TV show party, fandom fashion, outfit ideas","product_kw":["damon salvatore","blair waldorf","eddie diaz","evan peters","fitzgerald grant"],"show":"TV Culture","subject":"your favourite TV shows","fandom_desc":"the most binge-watched shows of the past few years","char_desc":"Damon Salvatore, Blair Waldorf, Eddie Diaz and the characters your watch party is celebrating","why_love":"the communal viewing experience, the shared love of a show, and wearing your fandom with pride","template":"lifestyle"},
    {"id":75,"title":"Festival Fashion: The Best Graphic Tees to Wear This Summer","seo_title":"Festival Fashion 2026: Best Graphic Tees to Wear This Summer","meta":"Festival season graphic tee guide — the vintage fan tees and celebrity merch that look great at any festival. Free UK shipping.","tags":"festival fashion, summer festival outfits, graphic tees, vintage style, Glastonbury, festival merch","product_kw":["courtney love","gwen stefani","serj tankian","damiano david","rosalia"],"show":"Music / Festival Culture","subject":"the music icons who define festival fashion","fandom_desc":"the world of live music and festival culture","char_desc":"Courtney Love, Gwen Stefani, Damiano David — the artists whose aesthetic belongs at a festival","why_love":"the energy, the fashion, and the way music icons inspire festival-goers year after year","template":"lifestyle"},
    {"id":76,"title":"Men's Vintage Graphic Tees: A Complete Style Guide for 2026","seo_title":"Men's Vintage Graphic Tees: A 2026 Style Guide","meta":"The complete guide to wearing men's vintage graphic tees in 2026. Styling tips, outfit ideas, and our top picks. Free UK shipping.","tags":"men's graphic tees, vintage style, men's fashion 2026, how to wear graphic tees, men's fan merch","product_kw":["al pacino","johnny depp","robert redford","ethan hawke","jon bernthal","sebastian stan"],"show":"Men's Fashion / Film","subject":"classic Hollywood and modern actor graphic tees","fandom_desc":"vintage cinema and the icons who defined cool for men","char_desc":"Al Pacino, Johnny Depp, Jon Bernthal and the actors who make great graphic tee subjects for men","why_love":"their cool credibility, their masculine energy, and the way a good actor tee just works","template":"lifestyle"},
    {"id":77,"title":"Women's Fan Tees: How to Style Celebrity Merch and Look Stylish","seo_title":"Women's Celebrity Fan Tees: How to Style Them and Look Great","meta":"How to style women's celebrity fan tees for any occasion. From casual to elevated — styling tips included. Free UK shipping.","tags":"women's fan tees, celebrity merch, how to style, women's fashion, vintage celebrity tee, fan merch","product_kw":["princess diana","blair waldorf","meryl streep","natalie portman","gwen stefani","courtney love"],"show":"Women's Fashion / Pop Culture","subject":"the icons women love to wear","fandom_desc":"the world of female-led pop culture and celebrity fashion","char_desc":"Princess Diana, Meryl Streep, Blair Waldorf — women whose style remains eternally iconic","why_love":"their strength, their style, and the way celebrating them through fashion feels genuinely empowering","template":"lifestyle"},
    {"id":78,"title":"How to Care for Your Graphic Tee and Make It Last for Years","seo_title":"How to Wash and Care for Your Graphic Tee | The Matcha Tee","meta":"Keep your graphic tees looking great for longer with these easy care tips. Washing, drying, and storage guide.","tags":"graphic tee care, how to wash graphic tee, print care, t-shirt maintenance, sustainable fashion","product_kw":["fitzwilliam darcy","eddie diaz","princess diana","leonardo dicaprio","blair waldorf"],"show":"Fashion Care","subject":"your graphic tee collection","fandom_desc":"quality print-on-demand graphic tees","char_desc":"our full range of vintage-style fan graphic tees","why_love":"the quality, the print detail, and the fact that proper care makes them last for years","template":"lifestyle"},
    {"id":79,"title":"Building a Fan Wardrobe: How to Mix Graphic Tees with Everyday Basics","seo_title":"Building a Fan Wardrobe: Graphic Tees & Everyday Basics","meta":"How to build a wardrobe that incorporates fan graphic tees naturally. Capsule wardrobe tips and outfit ideas. Free UK shipping.","tags":"capsule wardrobe, fan wardrobe, graphic tees, outfit ideas, mixing fan merch, fashion tips","product_kw":["princess diana","mr darcy","blair waldorf","evan peters","sebastian stan"],"show":"Personal Style","subject":"a fan-inspired capsule wardrobe","fandom_desc":"the art of building a genuinely stylish wardrobe around what you love","char_desc":"icons whose aesthetic translates into real everyday outfits — not just a fan costume","why_love":"the way great fan merch sits naturally in any casual wardrobe without screaming 'costume'","template":"lifestyle"},

    # Fandom roundups (extra)
    {"id":80,"title":"Best Disney Channel Nostalgia T-Shirts: 2000s TV Icons","seo_title":"Best Disney Channel Nostalgia T-Shirts: 2000s TV Fan Merch","meta":"Shop vintage-style Disney Channel nostalgia graphic tees. Mitchel Musso, Troy Bolton and 2000s icons with free UK shipping.","tags":"Disney Channel nostalgia, 2000s TV, Mitchel Musso, Troy Bolton, Hannah Montana, fan merch","product_kw":["mitchel musso","troy bolton","addison rae"],"show":"Disney Channel / 2000s TV","subject":"the icons of the Disney Channel era","fandom_desc":"the early 2000s Disney Channel golden age that defined a generation","char_desc":"Mitchel Musso, Troy Bolton and the characters that had us glued to Disney Channel every weekend","why_love":"the pure uncut nostalgia, the catchy music, and the way those shows genuinely hold up","template":"fan_roundup"},
    {"id":81,"title":"Best Comedy Legend Fan T-Shirts: Bernie Mac, Rick Moranis & Pauly Shore","seo_title":"Best Comedy Legend T-Shirts: Bernie Mac, Rick Moranis & Pauly Shore","meta":"Shop vintage-style comedy legend tribute tees. Bernie Mac, Rick Moranis, Pauly Shore graphic tees with free UK shipping.","tags":"comedy legends, Bernie Mac, Rick Moranis, Pauly Shore, stand-up comedy, tribute merch","product_kw":["bernie mac","rick moranis","pauly shore"],"show":"Comedy / Film","subject":"the comedy legends — Bernie Mac, Rick Moranis, and Pauly Shore","fandom_desc":"the golden era of comedy, from 80s cult films to 90s stand-up legends","char_desc":"Bernie Mac's fearless honesty, Rick Moranis's loveable nerd energy, and Pauly Shore's manic comedy","why_love":"their completely different comedic styles, their iconic films, and the nostalgia they carry","template":"fan_roundup"},
    {"id":82,"title":"Best Hollywood Actress Fan T-Shirts: Meryl Streep & Natalie Portman Gifts","seo_title":"Best Hollywood Actress T-Shirts: Meryl Streep & Natalie Portman","meta":"Shop vintage-style Hollywood actress graphic tees. Meryl Streep and Natalie Portman fan merch with free UK shipping.","tags":"Hollywood actresses, Meryl Streep, Natalie Portman, Oscar winners, fan merch, graphic tees","product_kw":["meryl streep","natalie portman"],"show":"Hollywood / Cinema","subject":"Meryl Streep and Natalie Portman","fandom_desc":"two of the greatest actresses Hollywood has ever produced","char_desc":"the three-time and two-time Oscar winners who have together dominated cinema for over four decades","why_love":"their fearless choices, their complete range, and the fact they never take the easy role","template":"fan_roundup"},
    {"id":83,"title":"Best Grunge & Alt Rock Fan T-Shirts: Courtney Love & Rock Icon Merch","seo_title":"Best Grunge Fan T-Shirts: Courtney Love & Alt Rock Merch","meta":"Shop vintage-style grunge and alt rock graphic tees. Courtney Love fan merch with free UK shipping.","tags":"grunge, alt rock, Courtney Love, Hole, rock music, vintage band tee, 90s music fan merch","product_kw":["courtney love","serj tankian"],"show":"Grunge / Alt Rock","subject":"Courtney Love and the icons of grunge and alt rock","fandom_desc":"the explosive grunge and alternative rock movement of the 90s","char_desc":"Courtney Love and the musicians who made raw, uncompromising music that still sounds urgent today","why_love":"the energy, the rawness, and the way grunge fashion is eternally cool decades later","template":"fan_roundup"},
    {"id":84,"title":"Best Reality TV Fan T-Shirts: Chrisley Knows Best & Pop Culture Gifts","seo_title":"Best Reality TV T-Shirts: Todd Chrisley & Reality Star Fan Gifts","meta":"Shop vintage-style reality TV fan graphic tees. Todd Chrisley and more reality star merch with free UK shipping.","tags":"reality TV, Todd Chrisley, Chrisley Knows Best, reality star fan merch, graphic tees","product_kw":["todd chrisley","addison rae","jenna marbles"],"show":"Reality TV / Pop Culture","subject":"the personalities who made reality TV worth watching","fandom_desc":"the golden era of reality TV and social media celebrity culture","char_desc":"Todd Chrisley, Addison Rae and the personalities who built real fanbases","why_love":"their unfiltered personalities, their entertaining chaos, and the way they built genuine communities","template":"fan_roundup"},
    {"id":85,"title":"Best Gifts for British Pop Culture Fans: David Attenborough, Tom Jones & Royals","seo_title":"Best British Pop Culture Fan Gifts: Attenborough, Tom Jones & Royals","meta":"Shop vintage-style British pop culture graphic tees. David Attenborough, Tom Jones, Princess Diana and more. Free UK shipping.","tags":"British pop culture, David Attenborough, Tom Jones, Princess Diana, British icons, fan merch","product_kw":["david attenborough","tom jones","princess diana","queen elizabeth","meghan markle","prince harry"],"show":"British Pop Culture","subject":"the icons of British culture","fandom_desc":"the uniquely British figures who shaped global pop culture","char_desc":"David Attenborough, Tom Jones, Princess Diana and the British icons the world genuinely loves","why_love":"their quintessentially British qualities, their global reach, and the pride they inspire","template":"fan_roundup"},
    {"id":86,"title":"Best Fan T-Shirts Under £30: Affordable Fan Gifts for Every Fandom","seo_title":"Best Fan T-Shirts Under £30: Affordable Fan Gifts","meta":"Shop the best fan graphic tees under £30. Affordable fan gifts for every fandom with free UK shipping.","tags":"fan gifts under £30, affordable fan merch, graphic tees, budget gifts, pop culture gifts","product_kw":["fitzwilliam darcy","eddie diaz","blair waldorf","leonardo dicaprio","evan peters"],"show":"Pop Culture","subject":"your favourite pop culture icons","fandom_desc":"the full world of film, TV, music, and celebrity culture","char_desc":"characters and icons from your favourite shows, films, and music — all available under £30","why_love":"the wearability, the personal connection, and the fact great fan merch doesn't have to cost a fortune","template":"gift_guide"},
    {"id":87,"title":"Best Pop Culture T-Shirts to Wear Right Now in 2026","seo_title":"Best Pop Culture T-Shirts to Wear Right Now in 2026","meta":"The hottest pop culture graphic tees to wear right now. Trending fan merch for 2026 with free UK shipping.","tags":"pop culture 2026, trending fan merch, graphic tees 2026, what to wear, celebrity tees","product_kw":["austin butler","evan peters","sebastian stan","byeon woo seok","cha eunwoo","addison rae"],"show":"2026 Pop Culture","subject":"the biggest names in pop culture right now","fandom_desc":"the cultural moment we're living in right now — from K-drama to blockbuster cinema","char_desc":"Austin Butler, Evan Peters, Sebastian Stan, Byeon Woo Seok — the faces dominating pop culture","why_love":"their relevance, their impact, and the way wearing them signals you're genuinely plugged in","template":"gift_guide"},
    {"id":88,"title":"Best Gifts for 2000s Kids: Nostalgia Tees From Your Favourite Era","seo_title":"Best 2000s Nostalgia Gifts: Fan T-Shirts From Your Favourite Era","meta":"Shop vintage-style 2000s nostalgia graphic tees. High School Musical, Hannah Montana, Disney Channel and more. Free UK shipping.","tags":"2000s nostalgia, 2000s gifts, Mitchel Musso, Troy Bolton, Hannah Montana, Y2K fashion","product_kw":["mitchel musso","troy bolton","jenna marbles","rob lowe","skeet ulrich"],"show":"2000s Pop Culture","subject":"the icons of the 2000s","fandom_desc":"the decade of Y2K fashion, dial-up internet, and some genuinely iconic pop culture moments","char_desc":"Troy Bolton, Mitchel Musso, Jenna Marbles — the faces of the 2000s you actually remember","why_love":"the unbeatable nostalgia, the revival of Y2K aesthetics in fashion, and the communal memory","template":"gift_guide"},
    {"id":89,"title":"Best Gifts for Latin Music Fans: Ricky Martin & Rosalia Merch","seo_title":"Best Latin Music Fan T-Shirts: Ricky Martin & Rosalia Gifts","meta":"Shop vintage-style Latin music fan graphic tees. Ricky Martin, Rosalia and more with free UK shipping.","tags":"Latin music, Ricky Martin, Rosalia, Latin pop, fan merch, music gifts, graphic tees","product_kw":["ricky martin","rosalia"],"show":"Latin Music","subject":"Ricky Martin and Rosalía","fandom_desc":"the vibrant world of Latin pop music","char_desc":"Ricky Martin, whose Livin' La Vida Loca defined the late 90s, and Rosalía, who is redefining the 2020s","why_love":"their undeniable charisma, their crossover appeal, and the way they make you want to dance","template":"fan_roundup"},
    {"id":90,"title":"Best Gifts for Indie Cinema Fans: Ethan Hawke & Rob Lowe Retro Tees","seo_title":"Best Indie Cinema Fan T-Shirts: Ethan Hawke & Rob Lowe Gifts","meta":"Shop vintage-style indie cinema fan graphic tees. Ethan Hawke, Rob Lowe and more with free UK shipping.","tags":"indie cinema, Ethan Hawke, Rob Lowe, Before Sunrise, Brat Pack, arthouse film, fan merch","product_kw":["ethan hawke","rob lowe","robert redford"],"show":"Indie Cinema / Brat Pack","subject":"Ethan Hawke, Rob Lowe and the indie cinema icons","fandom_desc":"the rich world of indie cinema and the Brat Pack era that preceded it","char_desc":"Ethan Hawke's intellectual lead roles, Rob Lowe's 80s charisma, and Robert Redford's timeless cool","why_love":"their artistic courage, their career longevity, and the genuinely great films they made","template":"fan_roundup"},
]

# ─── HTML Templates ───────────────────────────────────────────────────────────

def build_product_cards(products):
    if not products:
        return f"<p><a href='{DOMAIN}/collections/all'>Browse our full collection &rarr;</a></p>"
    cards = []
    for p in products:
        ptype = p.get("product_type", "T-Shirt")
        # No price shown — keeps the card from going stale and lets the product
        # page handle any USD/EUR currency conversion live.
        cards.append(f"""
<div style="border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin:16px 0;">
  <h3 style="margin:0 0 8px;font-size:17px;"><a href="{DOMAIN}/products/{p['handle']}" style="color:#1a1a1a;text-decoration:none;">{p['title']}</a></h3>
  <p style="margin:0 0 14px;color:#555;font-size:14px;">{ptype} &middot; Sizes S&ndash;5XL &middot; Free UK shipping</p>
  <a href="{DOMAIN}/products/{p['handle']}" style="display:inline-block;background:#1a1a1a;color:#fff;padding:9px 20px;border-radius:5px;text-decoration:none;font-size:13px;font-weight:600;">View product &rarr;</a>
</div>""")
    return "\n".join(cards)


INTROS = {
    "fan_roundup": [
        "<p>Finding the perfect gift for a <strong>{show}</strong> fan doesn&rsquo;t have to be difficult. Forget generic mugs and keyrings &mdash; a properly designed vintage graphic tee lets {audience} wear their passion every single day. At The Matcha Tee, we&rsquo;ve created a collection of retro-inspired tees and hoodies featuring {subject} that feel just as at home on the weekend as they do for a casual night out.</p>",
        "<p>If there&rsquo;s someone in your life obsessed with <strong>{show}</strong> &mdash; or let&rsquo;s be honest, if that someone is you &mdash; then you already know how hard it is to find merch that actually looks good. Most fan merchandise feels cheap or embarrassing to wear in public. That&rsquo;s where The Matcha Tee comes in: we design vintage-style graphic tees inspired by {subject} that fans genuinely want to wear.</p>",
        "<p>Whether you&rsquo;re buying for a birthday, Christmas, or just because, a well-made graphic tee is one of the best gifts you can give a <strong>{show}</strong> fan. Unlike one-use novelty gifts, a quality vintage tee gets worn again and again &mdash; every time showing off their love for {subject}. Our collection at The Matcha Tee is built exactly for that.</p>",
    ],
    "celebrity_tshirt": [
        "<p>Vintage-style celebrity tees have been a fashion staple for decades &mdash; and for good reason. A well-designed graphic tee referencing <strong>{subject}</strong> hits the sweet spot between fan culture and genuine wearable style. At The Matcha Tee, our retro-inspired collection captures the essence of {fandom_desc}, designed to look like a genuine 90s bootleg find rather than a cheap souvenir.</p>",
        "<p>There&rsquo;s something about a great vintage graphic tee that just works &mdash; especially when it celebrates <strong>{subject}</strong>. Whether you&rsquo;re a lifelong fan or you just appreciate the aesthetic, our collection at The Matcha Tee brings the bootleg-style designs fans love, printed on quality heavyweight cotton that actually lasts.</p>",
        "<p>A well-chosen graphic tee is more than merch &mdash; it&rsquo;s a statement about what you love. Our <strong>{subject}</strong> designs at The Matcha Tee are built around the bootleg aesthetic that&rsquo;s been part of pop culture since the 1970s: bold, worn-in, and genuinely cool. The kind of tee you&rsquo;d find in a vintage shop rather than a tourist gift store.</p>",
    ],
    "gift_guide": [
        "<p>Struggling to find the right gift for a <strong>{show}</strong> fan? You&rsquo;ve come to the right place. A vintage graphic tee sits in that perfect gift sweet spot: personal, wearable, and something they wouldn&rsquo;t necessarily buy for themselves. At The Matcha Tee, our entire collection is built around {char_desc}, so every purchase shows genuine thought.</p>",
        "<p>The best gifts aren&rsquo;t the most expensive &mdash; they&rsquo;re the most personal. For fans of <strong>{show}</strong>, a well-designed vintage graphic tee featuring {subject} says &ldquo;I know what you love&rdquo; in a way that lasts. Our collection at The Matcha Tee is curated for fans who take their fandoms seriously.</p>",
        "<p>Not all fan gifts are created equal. Novelty items get forgotten, gift cards feel impersonal, but a carefully chosen graphic tee? That gets worn. At The Matcha Tee, we make vintage-style tees for fans of <strong>{show}</strong> who actually want to wear their passion rather than just own it.</p>",
    ],
    "lifestyle": [
        "<p>Graphic tees have always been a cornerstone of casual fashion &mdash; but the vintage fan tee has had a serious resurgence. The key is wearing them well: pairing them right, picking the right fit, and choosing designs that feel authentic rather than tourist-souvenir cheap. At The Matcha Tee, we design specifically for fans who care about both what they wear and what it represents.</p>",
        "<p>The vintage bootleg aesthetic is everywhere right now &mdash; and it shows no signs of slowing down. From celebrity-worn oversized tees to carefully curated thrift-shop finds, the graphic tee has become one of the most versatile pieces in any wardrobe. Our collection at The Matcha Tee brings that same energy with print-on-demand quality and designs that actually last.</p>",
    ],
}

def hd(text):
    # one modest, controlled heading style — not the theme's giant default h2
    return f'<h2 style="font-size:20px;font-weight:600;line-height:1.3;margin:34px 0 14px;">{text}</h2>'


WHY_SECTIONS = [
    "Unlike novelty gifts that end up forgotten in a drawer, a good graphic tee gets worn again and again &mdash; a quiet nod to {subject} every time it goes on. The vintage bootleg look has had a real resurgence lately, with fans drawn to that worn-in, authentic feel over glossy licensed merch.",
    "Most fan merch is either too cheap or too corporate. Ours sits in the middle: bold, stylised designs printed on heavyweight cotton that holds up in the wash, with a relaxed unisex fit that flatters any body type and a size range that runs all the way to 5XL.",
]

QUALITY = (
    "Every tee comes in sizes <strong>S&ndash;5XL</strong> (hoodies to 4XL), and every UK order ships "
    "<strong>free</strong>, usually arriving within 5&ndash;10 working days. Because we print to order, each "
    "one is made fresh for you &mdash; well worth the short wait. Not sure on size? Our "
    f'<a href="{DOMAIN}/blogs/style-guide/unisex-t-shirt-sizing-guide-how-to-get-the-perfect-fit">sizing guide</a> '
    "has all the measurements."
)

FAQS = {
    "fan_roundup": [
        ("Do you ship outside the UK?", "Yes &mdash; we ship worldwide. UK orders are free; international orders have a flat rate added at checkout."),
        ("What sizes do you offer?", "Tees run S to 5XL and hoodies up to 4XL, with a small surcharge from 3XL up."),
        ("How do I wash my graphic tee?", "Turn it inside out and wash cool (30&deg;C or below). Air dry where you can &mdash; it keeps the print crisp for much longer."),
        ("How long does delivery take?", "UK orders arrive in 5&ndash;10 working days. We print to order, so allow a day or two for production before dispatch."),
    ],
    "celebrity_tshirt": [
        ("Are these officially licensed?", "They&rsquo;re fan-made tribute tees in the vintage bootleg style &mdash; the kind of unofficial merch that&rsquo;s been part of fan culture for decades. Designed by fans, for fans."),
        ("What&rsquo;s the print quality like?", "We use direct-to-garment printing on heavyweight cotton, so prints stay sharp through plenty of washes &mdash; just keep it to a cold wash and air dry."),
        ("What sizes do you offer?", "Tees run S to 5XL and hoodies up to 4XL. Full measurements are in our sizing guide."),
        ("How long does delivery take?", "UK orders ship free and arrive in 5&ndash;10 working days. We print to order, so allow a day or two for production first."),
    ],
    "gift_guide": [
        ("What size should I buy as a gift?", "When in doubt, size up &mdash; the relaxed vintage fit means a slightly larger size still looks intentional. Our sizing guide has reference measurements."),
        ("How long does UK delivery take?", "5&ndash;10 working days. For a specific occasion, order with about a week to spare to be safe."),
        ("Do you ship internationally?", "Yes &mdash; UK ships free, international ships at a flat rate that varies by country."),
        ("How do I care for the tee?", "Cold wash inside out (30&deg;C max) and air dry. That keeps the print sharp and the fabric from shrinking."),
    ],
    "lifestyle": [
        ("What&rsquo;s the best way to style a graphic tee?", "Keep everything else simple &mdash; dark jeans or chinos, clean trainers &mdash; and let the tee be the focal point. A slight front-tuck adds shape without looking too formal."),
        ("Are your tees unisex?", "Yes &mdash; every tee uses a relaxed unisex cut that works for any body type. See our sizing guide for measurements."),
        ("How do I keep it looking good?", "Cold wash (30&deg;C max), inside out, air dry. That keeps the print sharp and stops shrinkage."),
        ("Do you ship internationally?", "Yes. UK orders ship free; international orders have a flat rate shown at checkout."),
    ],
}


def build_faq(tmpl):
    items = FAQS.get(tmpl, FAQS["fan_roundup"])
    rows = [hd("Good to know")]
    for q, a in items:
        rows.append(f'<p style="margin:18px 0 2px;font-weight:600;">{q}</p>')
        rows.append(f'<p style="margin:0;">{a}</p>')
    return "\n".join(rows)


def build_post(topic, products):
    tmpl  = topic["template"]
    show  = topic["show"]
    subj  = topic["subject"]
    char  = topic.get("char_desc", subj)
    fandom = topic.get("fandom_desc", show)
    why_love = topic.get("why_love", "their stories and enduring cultural impact")
    audience = f"{show} fans"

    intro_pool = INTROS.get(tmpl, INTROS["fan_roundup"])
    intro = random.choice(intro_pool).format(
        show=show, subject=subj, audience=audience,
        char_desc=char, fandom_desc=fandom
    )
    why    = random.choice(WHY_SECTIONS).format(subject=subj)
    faq    = build_faq(tmpl)
    cards  = build_product_cards(products)
    browse = f'<p style="margin-top:26px;"><a href="{DOMAIN}/collections/all">Browse the full collection &rarr;</a></p>'

    if tmpl == "lifestyle":
        body = f"""
{intro}

{hd("How to wear it well")}
<p>The difference between a great graphic-tee outfit and a costume comes down to styling. Keep the rest simple &mdash; dark jeans or chinos, plain trainers, no competing patterns &mdash; and let the tee carry the look. A slight front-tuck adds shape, and layering under an open shirt works for cooler days.</p>
<p>{QUALITY}</p>

{hd("Our collection")}
{cards}

{faq}

{browse}
"""
    elif tmpl == "celebrity_tshirt":
        body = f"""
{intro}

{hd(f"Shop {subj} tees")}
{cards}

{hd("Why these designs work")}
<p>The appeal of {fandom} goes beyond the screen &mdash; fans love {why_love}. Each design takes its cue from the bootleg tee tradition: bold graphics, worn-in colour, and typography that feels authentic rather than corporate, all printed to order on heavyweight cotton.</p>
<p>{why}</p>
<p>{QUALITY}</p>

{faq}

{browse}
"""
    elif tmpl == "gift_guide":
        body = f"""
{intro}

{hd("Our top picks")}
{cards}

{hd("Why a graphic tee makes a great gift")}
<p>A well-chosen tee beats most novelty gifts: it&rsquo;s wearable, personal, and actually gets used. The vintage look reads as cool even to people who don&rsquo;t know the reference &mdash; no loud licensed logos, just a clean graphic that fits any casual wardrobe. The love for {fandom} runs deep, and a tee that nods to it lasts far longer than a mug.</p>
<p>{QUALITY}</p>

{faq}

{browse}
"""
    else:  # fan_roundup (default)
        body = f"""
{intro}

{hd(f"Shop our {show} tees")}
{cards}

{hd(f"Why {show} fans love a vintage tee")}
<p>The appeal of {fandom} goes beyond the screen &mdash; fans love {why_love}. A vintage-style tee lets you carry that into your everyday wardrobe, with the kind of worn-in, authentic look fans actually want to be seen in rather than mass-produced licensed merch.</p>
<p>{why}</p>
<p>{QUALITY}</p>

{faq}

{browse}
"""
    return body.strip()


# ─── Shopify helpers ──────────────────────────────────────────────────────────

def fetch_products():
    products = []
    url = f"{API}/products.json?limit=250&fields=id,title,handle,product_type,variants,images"
    while url:
        r = httpx.get(url, headers=RH, timeout=30)
        data = r.json()["products"]
        for p in data:
            v0   = p["variants"][0] if p.get("variants") else {}
            imgs = p.get("images", [])
            products.append({
                "id":           p["id"],
                "title":        p["title"],
                "handle":       p["handle"],
                "product_type": p.get("product_type", "T-Shirt"),
                "price":        v0.get("price", "27.00"),
                "image_url":    imgs[0]["src"] if imgs else None,
            })
        link = r.headers.get("Link","")
        url  = None
        for part in link.split(","):
            if 'rel="next"' in part: url = part.strip().split(";")[0].strip("<> ")
    return products


def fetch_existing_titles():
    r = httpx.get(f"{API}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,title",
                  headers=RH, timeout=15)
    return [a["title"].lower() for a in r.json().get("articles",[])]


def match_products(topic, all_products, max_products=5):
    kws  = [k.lower() for k in topic["product_kw"]]
    out  = []
    for p in all_products:
        t = p["title"].lower()
        if any(k in t for k in kws):
            out.append(p)
    return out[:max_products]


def upload_article(topic, body_html, image_url=None):
    art = {
        "title":        topic["title"],
        "body_html":    body_html,
        "summary_html": topic["meta"],
        "tags":         topic["tags"],
        "published":    True,
        "metafields": [
            {"namespace":"global","key":"title_tag",       "value":topic["seo_title"],"type":"single_line_text_field"},
            {"namespace":"global","key":"description_tag", "value":topic["meta"],      "type":"single_line_text_field"},
        ],
    }
    if image_url:
        art["image"] = {"src": image_url, "alt": topic["title"]}
    r = httpx.post(f"{API}/blogs/{BLOG_ID}/articles.json", headers=H,
                   json={"article": art}, timeout=30)
    if r.status_code not in (200,201):
        print(f"  Upload error {r.status_code}: {r.text[:200]}")
        return None
    return f"{DOMAIN}/blogs/style-guide/{r.json()['article']['handle']}"


def fetch_article_map():
    """title.lower() -> {id, handle, has_image}"""
    out = {}
    r = httpx.get(f"{API}/blogs/{BLOG_ID}/articles.json?limit=250&fields=id,title,handle,image",
                  headers=RH, timeout=20)
    for a in r.json().get("articles", []):
        out[a["title"].lower()] = {
            "id": a["id"], "handle": a["handle"], "has_image": bool(a.get("image")),
        }
    return out


def update_article(article_id, body_html, image_url=None, set_image=False):
    art = {"id": article_id, "body_html": body_html}
    if set_image and image_url:
        art["image"] = {"src": image_url}
    r = httpx.put(f"{API}/blogs/{BLOG_ID}/articles/{article_id}.json", headers=H,
                  json={"article": art}, timeout=30)
    if r.status_code not in (200, 201):
        print(f"  Update error {r.status_code}: {r.text[:200]}")
        return False
    return True


def reformat_posted():
    """Rebuild every already-posted topic with the clean format + ensure an image."""
    print("Fetching products and existing articles...")
    all_products = fetch_products()
    amap         = fetch_article_map()
    print(f"  {len(all_products)} products  |  {len(amap)} articles live\n")

    done = 0
    for topic in TOPICS:
        meta = amap.get(topic["title"].lower())
        if not meta:
            continue  # not posted yet — skip
        products  = match_products(topic, all_products)
        image_url = products[0].get("image_url") if products else None
        body      = build_post(topic, products)
        # attach image only if the article doesn't already have one
        set_img   = (not meta["has_image"]) and bool(image_url)
        ok = update_article(meta["id"], body, image_url, set_image=set_img)
        img_note  = " +img" if set_img else ""
        print(f"  [{topic['id']:2d}] {'OK ' if ok else 'ERR'}{img_note}  {topic['title']}")
        if ok:
            done += 1
        time.sleep(0.8)
    print(f"\nReformatted {done} articles with the clean layout.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(topic_ids=None, list_only=False, batch=None):
    print("Fetching products and existing articles...")
    all_products = fetch_products()
    existing     = fetch_existing_titles()
    print(f"  {len(all_products)} products  |  {len(existing)} articles already posted\n")

    unposted = [t for t in TOPICS if t["title"].lower() not in existing]
    posted   = [t for t in TOPICS if t["title"].lower() in existing]

    if list_only:
        print("══ TOPIC QUEUE (90 topics) ══════════════════════════════")
        for t in TOPICS:
            status = "POSTED" if t["title"].lower() in existing else "pending"
            prods  = match_products(t, all_products)
            mark   = "+" if status == "POSTED" else " "
            print(f"  [{t['id']:2d}] [{mark}] ({len(prods)}p)  {t['title']}")
        print(f"\n  {len(posted)} posted  |  {len(unposted)} remaining")
        return

    if topic_ids:
        to_post = [t for t in TOPICS if t["id"] in topic_ids]
    elif batch:
        to_post = unposted[:batch]
    else:
        to_post = [unposted[0]] if unposted else []

    if not to_post:
        print("All 90 topics posted! Add more topics to the TOPICS list.")
        return

    for topic in to_post:
        print(f"Posting [{topic['id']:2d}]: {topic['title']}")
        products  = match_products(topic, all_products)
        image_url = products[0].get("image_url") if products else None
        print(f"  products: {[p['title'][:30] for p in products]}")
        print(f"  image:    {'yes' if image_url else 'none'}")
        body = build_post(topic, products)
        url  = upload_article(topic, body, image_url)
        if url:
            print(f"  live: {url}")
        else:
            print(f"  FAILED")
        time.sleep(1.2)

    print(f"\nDone. {len(unposted) - len(to_post)} topics still remaining.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",  action="store_true", help="Show queue status")
    parser.add_argument("--all",   action="store_true", help="Post all remaining")
    parser.add_argument("--batch", type=int,             help="Post next N topics")
    parser.add_argument("--topic", type=int, nargs="+",  help="Post specific IDs")
    parser.add_argument("--update", action="store_true", help="Rebuild all posted articles with the clean format")
    args = parser.parse_args()

    if args.update:
        reformat_posted()
    elif args.list:
        run(list_only=True)
    elif args.all:
        existing     = fetch_existing_titles()
        unposted_ids = [t["id"] for t in TOPICS if t["title"].lower() not in existing]
        run(topic_ids=unposted_ids)
    elif args.topic:
        run(topic_ids=args.topic)
    elif args.batch:
        run(batch=args.batch)
    else:
        run()
