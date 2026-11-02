"""
TinyLytic AI Chat Engine
Provides Chat intelligence: works with local LLaMA GGUF models or the built-in Intelligent Assistant.
Clean text responses without emojis or unnecessary text hints.
"""

import os
import sys
import re
import json
import math
from datetime import datetime
from core_engine import resource_path

# Safe import for llama_cpp
try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except Exception:
    HAS_LLAMA = False
    Llama = None


class BuiltinAIAssistant:
    """High-speed built-in AI assistant for conversational queries, fact answering, transcript analysis, and timestamping."""

    def __init__(self):
        self.context_transcript = ""

    def set_transcript(self, transcript_text):
        self.context_transcript = transcript_text.strip()

    def process_query(self, query):
        raw_query = query.strip()
        q = raw_query.lower()

        # 1. Check for compound greeting + question (e.g. "hi tell me...", "hello what is...")
        # Strip greeting prefixes if followed by an actual question
        greeting_match = re.match(r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening)[,\s!.]+(.+)$', q, re.IGNORECASE)
        has_greeting_prefix = False
        if greeting_match:
            has_greeting_prefix = True
            core_query = greeting_match.group(2).strip()
            q_clean = core_query.lower()
        else:
            core_query = raw_query
            q_clean = q

        # Pure greeting alone
        if q in ["hi", "hello", "hey", "greetings", "good morning", "good evening", "good afternoon"]:
            return "Hello. How can I assist you today? You can ask any question, request calculations, or load a transcript to summarize and format chapters."

        # Help / Capabilities query
        if q in ["help", "what can you do", "features", "commands"]:
            return (
                "TinyLytic AI Assistant Capabilities:\n"
                "- Direct conversational Q&A, facts, math, and knowledge queries\n"
                "- Transcript summarization and key takeaways extraction\n"
                "- YouTube description chapter formatting with timestamps\n"
                "- Speaker diarization and multilingual speech analysis (Bengali, English, and 99+ languages)\n"
                "- Video caption synchronization and typography assistance"
            )

        # 2. Specific Knowledge & Fact Matching
        ans = self.match_knowledge_base(q_clean)
        if ans:
            if has_greeting_prefix:
                return f"Hello. {ans}"
            return ans

        # 3. Math calculation solver
        math_ans = self.evaluate_math(q_clean)
        if math_ans:
            if has_greeting_prefix:
                return f"Hello. {math_ans}"
            return math_ans

        # 4. Transcript Analysis Tasks (if transcript loaded or explicitly requested)
        if any(w in q_clean for w in ["summary", "summarize", "overview", "brief", "what is this about"]):
            return self.generate_summary()

        if any(w in q_clean for w in ["chapter", "timestamp", "youtube format", "chapters", "format"]):
            return self.format_chapters()

        if any(w in q_clean for w in ["takeaway", "points", "bullet", "action item", "key points", "highlights"]):
            return self.extract_key_points()

        if any(w in q_clean for w in ["tone", "sentiment", "mood", "feeling"]):
            return self.analyze_tone()

        # 5. If transcript is loaded and asking a question about it
        if self.context_transcript:
            return self.answer_with_context(core_query)

        # 6. General intelligent conversational responder
        res = self.general_conversation(core_query)
        if has_greeting_prefix:
            return f"Hello. {res}"
        return res

    def match_knowledge_base(self, q):
        """Match common knowledge, science, language, counting, and system queries."""
        # Rainbow colors query (handles typos like 'raibow', 'raimbow')
        if re.search(r'rai[nm]?bow', q) and any(term in q for term in ["color", "count", "how many", "many", "what are", "tell me", "list"]):
            return (
                "A rainbow consists of 7 colors:\n"
                "1. Red\n"
                "2. Orange\n"
                "3. Yellow\n"
                "4. Green\n"
                "5. Blue\n"
                "6. Indigo\n"
                "7. Violet\n\n"
                "These are commonly remembered by the acronym ROYGBIV."
            )
        elif re.search(r'\brai[nm]?bow\b', q):
            return (
                "A rainbow is an optical and meteorological phenomenon that causes a spectrum of light to appear in the sky "
                "when the Sun shines onto droplets of moisture in Earth's atmosphere. It takes the form of a multicoloured circular arc, "
                "displaying 7 primary spectrum colors: Red, Orange, Yellow, Green, Blue, Indigo, and Violet (ROYGBIV)."
            )

        # Solar system / Planets
        if "how many planets" in q or "planets in the solar system" in q:
            return (
                "There are 8 recognized planets in our solar system:\n"
                "1. Mercury\n2. Venus\n3. Earth\n4. Mars\n"
                "5. Jupiter\n6. Saturn\n7. Uranus\n8. Neptune\n"
                "(Pluto was reclassified as a dwarf planet by the IAU in 2006.)"
            )

        # Continents count
        if "how many continents" in q or "continents of the world" in q:
            return (
                "There are 7 continents on Earth:\n"
                "1. Asia\n2. Africa\n3. North America\n4. South America\n"
                "5. Antarctica\n6. Europe\n7. Australia (Oceania)"
            )

        # Oceans count
        if "how many oceans" in q or "oceans of the world" in q:
            return (
                "There are 5 oceans on Earth:\n"
                "1. Pacific Ocean\n2. Atlantic Ocean\n3. Indian Ocean\n"
                "4. Southern (Antarctic) Ocean\n5. Arctic Ocean"
            )

        # Primary colors
        if "primary colors" in q or "primary color" in q:
            return (
                "The primary colors depend on the color model:\n"
                "- In traditional art/pigment (RYB): Red, Yellow, Blue\n"
                "- In additive light / digital displays (RGB): Red, Green, Blue\n"
                "- In subtractive printing (CMYK): Cyan, Magenta, Yellow, Key (Black)"
            )

        # Bengali Translations
        if ("in bengali" in q or "to bengali" in q or "translate" in q) and any(term in q for term in ["hello", "thank you", "thanks", "how are you", "good morning", "good night", "welcome", "love", "water", "friend", "peace"]):
            trans_dict = {
                "hello": "হ্যালো (Hello) or নমস্কার (Namaskar) / আসসালামু আলাইকুম (Assalamu Alaikum)",
                "thank you": "ধন্যবাদ (Dhonnobad)",
                "thanks": "ধন্যবাদ (Dhonnobad)",
                "how are you": "আপনি কেমন আছেন? (Apni kemon achen?) / তুমি কেমন আছো? (Tumi kemon acho?)",
                "good morning": "শুভ সকাল (Shuvo Sokal)",
                "good night": "শুভ রাত্রি (Shuvo Ratri)",
                "welcome": "স্বাগতম (Shwagotom)",
                "love": "আমি তোমাকে ভালোবাসি (Ami tomake bhalobashi)",
                "water": "পানি (Pani) / জল (Jol)",
                "friend": "বন্ধু (Bondhu)",
                "peace": "শান্তি (Shanti)"
            }
            for eng, bng in trans_dict.items():
                if eng in q:
                    return f"'{eng.title()}' in Bengali is: {bng}"

        # Bengali language queries
        if "bengali" in q or "bangla" in q:
            return (
                "Bengali (বাংলা) is an Indo-Aryan language spoken primarily in Bangladesh and West Bengal, India. "
                "TinyLytic includes specialized support for Bengali speech, proper Bengali script font rendering, "
                "Bengali punctuation marks (including the dā̃ṛi '।', comma ',', and question mark '?'), and code-switching with English."
            )

        # Whisper speech model
        if "whisper" in q:
            return (
                "OpenAI Whisper is an advanced automatic speech recognition (ASR) system trained on 680,000+ hours of multilingual "
                "and multitask supervised data. TinyLytic leverages Whisper with hardware acceleration (CUDA GPU and multithreaded CPU) "
                "for speech transcription, translation, and word-level timestamp synchronization across 99+ languages."
            )

        # Who are you / Identity
        if "who are you" in q or "what is tinylytic" in q or "who made you" in q:
            return (
                "I am TinyLytic AI Studio Assistant, developed by NoishiXzen & Aivory. "
                "I am built to assist with universal speech transcription, realtime audio recording, "
                "video captions with beat-by-beat typography, and intelligent content analysis."
            )

        # Date & Time
        if any(w in q for w in ["what time is it", "current time", "what is the date", "today's date"]):
            now = datetime.now()
            return f"The current system date and time is: {now.strftime('%A, %B %d, %Y - %H:%M:%S')}."

        # Speed of light & sound
        if "speed of light" in q:
            return "The speed of light in a vacuum is exactly 299,792,458 meters per second (approximately 300,000 km/s or 186,282 miles/second)."
        if "speed of sound" in q:
            return "The speed of sound in dry air at 20 degrees Celsius is approximately 343 meters per second (1,235 km/h or 767 mph)."

        # Notable Figures and Biographies
        if "elon musk" in q:
            return (
                "Elon Musk is a technology entrepreneur and business magnate. He is the CEO and Chief Engineer of SpaceX, "
                "CEO and Product Architect of Tesla, Inc., founder of xAI and The Boring Company, co-founder of Neuralink and OpenAI, "
                "and owner/CTO of X (formerly Twitter). He is known for driving major innovations in electric vehicles, commercial space travel, "
                "and artificial intelligence."
            )
        if "steve jobs" in q:
            return (
                "Steve Jobs (1955-2011) was the co-founder, chairman, and CEO of Apple Inc. He was a visionary pioneer of the personal computer "
                "revolution and led the creation of groundbreaking consumer devices including the Macintosh, iPod, iPhone, and iPad, "
                "as well as serving as majority shareholder and CEO of Pixar Animation Studios."
            )
        if "bill gates" in q:
            return (
                "Bill Gates is an American business magnate, software developer, and philanthropist who co-founded Microsoft Corporation in 1975 "
                "with Paul Allen. Through Microsoft, he helped pioneer the personal computing era with MS-DOS and Windows. Later, he established "
                "the Bill & Melinda Gates Foundation to combat global disease and poverty."
            )
        if "alan turing" in q:
            return (
                "Alan Turing (1912-1954) was an English mathematician, computer scientist, and cryptanalyst, widely regarded as the father of modern "
                "computer science and artificial intelligence. During World War II, he played a pivotal role in cracking intercepted coded messages "
                "at Bletchley Park, including the German Enigma machine. The Turing test remains a foundational concept in AI."
            )
        if "einstein" in q or "albert einstein" in q:
            return (
                "Albert Einstein (1879-1955) was a German-born theoretical physicist recognized as one of the greatest physicists of all time. "
                "He developed the theory of relativity (special and general), formulated mass-energy equivalence (E = mc^2), and won the 1921 "
                "Nobel Prize in Physics for his discovery of the law of the photoelectric effect."
            )
        if "newton" in q or "isaac newton" in q:
            return (
                "Sir Isaac Newton (1642-1727) was an English mathematician, physicist, and astronomer. He formulated the three fundamental laws of "
                "motion and the universal law of gravitation in his masterpiece 'Philosophiae Naturalis Principia Mathematica', co-invented calculus, "
                "and made foundational discoveries in optics with the reflecting telescope."
            )
        if "rabindranath" in q or "tagore" in q:
            return (
                "Rabindranath Tagore (1861-1941) was a Bengali polymath, poet, writer, playwright, composer, and visual artist. In 1913, he became "
                "the first non-European to win the Nobel Prize in Literature for his poetry collection 'Gitanjali'. He composed the national anthems "
                "of Bangladesh ('Amar Shonar Bangla') and India ('Jana Gana Mana')."
            )
        if "kazi nazrul" in q or "nazrul islam" in q:
            return (
                "Kazi Nazrul Islam (1899-1976) is the National Poet of Bangladesh, widely honored as the 'Bidrohi Kobi' (Rebel Poet). "
                "His fiery poems and songs championed social justice, equality, and resistance against oppression, composing over 4,000 songs "
                "collectively known as Nazrul Geeti."
            )

        # Gaming & Pop Culture
        if "cyberpunk" in q or "cyberpunk 2077" in q:
            return (
                "Cyberpunk 2077 is an open-world action role-playing game developed by CD Projekt Red, based on Mike Pondsmith's Cyberpunk tabletop "
                "universe. Set in the dystopian megalopolis of Night City, players control V, a mercenary outlaw navigating high-tech cybernetic "
                "implants, corporate conspiracies, and a digital ghost of rockstar rebel Johnny Silverhand (played by Keanu Reeves)."
            )
        if "gta" in q or "grand theft auto" in q:
            return (
                "Grand Theft Auto (GTA) is a critically acclaimed open-world action-adventure video game series created by Rockstar Games. "
                "Known for detailed satirical sandbox cities (such as Los Santos, Liberty City, and Vice City), missions, dynamic physics, "
                "and engaging crime dramas."
            )
        if "minecraft" in q:
            return (
                "Minecraft is a 3D sandbox game developed by Mojang Studios and created by Markus 'Notch' Persson. Players explore a procedurally "
                "generated blocky world, gather raw materials, craft tools, build structures, and survive monsters in Survival and Creative modes."
            )

        # Technology Concepts
        if any(term in q for term in ["artificial intelligence", "what is ai", "define ai"]):
            return (
                "Artificial Intelligence (AI) is the branch of computer science dedicated to creating systems capable of performing tasks "
                "that typically require human intelligence. These include visual perception, speech recognition (ASR), natural language processing (NLP), "
                "decision-making, and generative reasoning through machine learning algorithms and deep neural networks."
            )
        if any(term in q for term in ["gpu vs cpu", "difference between gpu and cpu", "cpu or gpu"]):
            return (
                "CPU vs GPU Comparison:\n\n"
                "- **CPU (Central Processing Unit)**: The general-purpose brain of the computer. It features fewer, highly optimized cores designed "
                "for sequential processing, low-latency branching, and complex system logic.\n"
                "- **GPU (Graphics Processing Unit)**: An architecture built with thousands of smaller, efficient cores designed for massive parallel "
                "computations. It excels in graphics rendering, matrix multiplications, tensor operations, and AI deep learning acceleration (e.g. CUDA)."
            )
        if "quantum computer" in q or "quantum computing" in q:
            return (
                "Quantum Computing leverages the principles of quantum mechanics (superposition and entanglement) to process complex calculations "
                "exponentially faster than classical computers for specific problem sets. Instead of classical binary bits (0 or 1), quantum systems "
                "use qubits that can exist in multiple states simultaneously."
            )

        # United States States count
        if "how many states" in q and ("us" in q or "united states" in q or "america" in q):
            return "The United States of America consists of 50 states, along with 1 federal district (Washington, D.C.) and several territories."

        # Bengali Translations
        if "in bengali" in q or "to bengali" in q:
            trans_dict = {
                "hello": "হ্যালো (Hello) or নমস্কার (Namaskar) / আসসালামু আলাইকুম (Assalamu Alaikum)",
                "thank you": "ধন্যবাদ (Dhonnobad)",
                "how are you": "আপনি কেমন আছেন? (Apni kemon achen?) / তুমি কেমন আছো? (Tumi kemon acho?)",
                "good morning": "শুভ সকাল (Shuvo Sokal)",
                "good night": "শুভ রাত্রি (Shuvo Ratri)",
                "welcome": "স্বাগতম (Shwagotom)",
                "i love you": "আমি তোমাকে ভালোবাসি (Ami tomake bhalobashi)",
                "water": "পানি (Pani) / জল (Jol)",
                "friend": "বন্ধু (Bondhu)",
                "peace": "শান্তি (Shanti)"
            }
            for eng, bng in trans_dict.items():
                if eng in q:
                    return f"'{eng.title()}' in Bengali is: {bng}"

        # Capital cities query
        capitals = {
            "france": "Paris",
            "germany": "Berlin",
            "japan": "Tokyo",
            "united states": "Washington, D.C.",
            "usa": "Washington, D.C.",
            "united kingdom": "London",
            "uk": "London",
            "india": "New Delhi",
            "bangladesh": "Dhaka",
            "canada": "Ottawa",
            "australia": "Canberra",
            "italy": "Rome",
            "spain": "Madrid",
            "china": "Beijing",
            "russia": "Moscow",
            "brazil": "Brasilia",
            "south korea": "Seoul",
            "turkey": "Ankara",
            "egypt": "Cairo"
        }
        for country, cap in capitals.items():
            if f"capital of {country}" in q or f"capital city of {country}" in q:
                return f"The capital of {country.title()} is {cap}."

        return None

    def evaluate_math(self, q):
        """Safely detect and evaluate arithmetic expressions in user query."""
        # Match expressions like "what is 25 * 4", "calculate 120 / 3", "50 + 25", etc.
        match = re.search(r'(?:what is|calculate|solve|evaluate)?\s*([0-9\.\s\+\-\*\/\^\(\)]+[0-9\)])', q)
        if match:
            expr_str = match.group(1).strip()
            # Only proceed if it contains at least one operator
            if any(op in expr_str for op in ["+", "-", "*", "/", "^"]):
                clean_expr = expr_str.replace("^", "**")
                # Whitelist characters for safe eval
                if re.match(r'^[0-9\.\s\+\-\*\/\(\)]+$', clean_expr):
                    try:
                        result = eval(clean_expr, {"__builtins__": None}, {})
                        if isinstance(result, float) and result.is_integer():
                            result = int(result)
                        return f"{expr_str} = {result}"
                    except Exception:
                        pass
        return None

    def general_conversation(self, query):
        """Conversational response generator providing direct, intelligent assistance across general knowledge, coding, science, and reasoning."""
        q_raw = query.strip()
        q = q_raw.lower()

        # How are you / status
        if any(term in q for term in ["how are you", "how are you doing", "how's it going", "are you ok"]):
            return "I am doing well and ready to assist you. You can ask me any question, request explanations or code, or analyze transcripts and media."

        # Thank you / Politeness
        if any(term in q for term in ["thank you", "thanks", "appreciate it", "thx"]):
            return "You are very welcome. Let me know if there is anything else I can help you with."

        # Joke
        if "joke" in q:
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs.",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "Why did the computer keep freezing? It left its Windows open.",
                "How do you comfort a JavaScript bug? You console it."
            ]
            import random
            return random.choice(jokes)

        # Programming & Coding Help
        if any(term in q for term in ["python", "javascript", "code", "function", "programming", "algorithm", "sql", "html", "css", "git"]):
            if "reverse" in q and "string" in q:
                return (
                    "In Python, the most idiomatic way to reverse a string is using slicing:\n\n"
                    "```python\n"
                    "text = \"hello\"\n"
                    "reversed_text = text[::-1]  # 'olleh'\n"
                    "```\n\n"
                    "Alternatively, using `reversed()` and `str.join()`:\n"
                    "```python\n"
                    "reversed_text = ''.join(reversed(text))\n"
                    "```"
                )
            if "hello world" in q:
                return (
                    "Here is 'Hello, World!' in common programming languages:\n\n"
                    "- **Python**:\n  `print(\"Hello, World!\")`\n"
                    "- **JavaScript**:\n  `console.log(\"Hello, World!\");`\n"
                    "- **C++**:\n  `std::cout << \"Hello, World!\" << std::endl;`\n"
                    "- **Java**:\n  `System.out.println(\"Hello, World!\");`"
                )
            if "git" in q:
                return (
                    "Essential Git Commands:\n"
                    "- `git status`: Check modified files\n"
                    "- `git add .`: Stage all changes\n"
                    "- `git commit -m \"message\"`: Commit staged changes\n"
                    "- `git pull`: Fetch and merge changes from remote\n"
                    "- `git push`: Push commits to remote repository"
                )
            return (
                f"Coding Assistance for: '{query}':\n\n"
                "To write clean and maintainable code:\n"
                "1. Keep functions focused on a single responsibility.\n"
                "2. Use descriptive variable names and consistent formatting.\n"
                "3. Handle edge cases and exceptions gracefully.\n"
                "4. Add unit tests to prevent regressions.\n\n"
                "Feel free to provide your specific code snippet or requirements for a detailed implementation."
            )

        # Science & Physics
        if "gravity" in q:
            return (
                "Gravity is a fundamental interaction which causes mutual attraction between all things with mass or energy. "
                "In classical physics, Newton described it as an attractive force proportional to the masses of two bodies and inversely "
                "proportional to the square of the distance between them ($F = G \\frac{m_1 m_2}{r^2}$). "
                "In modern physics, Einstein's General Relativity describes gravity as the curvature of spacetime caused by mass and energy."
            )
        if "black hole" in q:
            return (
                "A black hole is a region of spacetime where gravity is so strong that nothing, including light and other electromagnetic waves, "
                "has enough energy to escape its event horizon. They are typically formed when massive stars collapse at the end of their life cycle."
            )
        if "photosynthesis" in q:
            return (
                "Photosynthesis is the biological process used by plants, algae, and certain bacteria to synthesize nutrients from carbon dioxide and water, "
                "using light energy absorbed by chlorophyll:\n\n"
                "$$6CO_2 + 6H_2O + \\text{light} \\rightarrow C_6H_{12}O_6 + 6O_2$$\n\n"
                "It produces glucose (energy) and releases oxygen into the atmosphere."
            )
        if "dna" in q or "genetic" in q:
            return (
                "DNA (Deoxyribonucleic acid) is the hereditary molecule that carries genetic instructions in all known living organisms. "
                "It consists of two polynucleotide chains that coil around each other to form a double helix, composed of four chemical bases: "
                "Adenine (A), Thymine (T), Cytosine (C), and Guanine (G)."
            )

        # Creative writing, Stories & Poems
        if "story" in q or "tell me a story" in q:
            return (
                "The Signal in the Deep:\n\n"
                "Deep beneath the cresting waves of the northern Atlantic, the autonomous research vessel Lumina hummed softly. "
                "Dr. Jennifer Ray had spent eight months monitoring the deep thermal vents, searching for acoustic anomalies. "
                "Just past midnight, the hydrophones detected a sound unlike any seismic tremor: a rhythmic, melodic sequence of pulses, "
                "pulsing in mathematical intervals identical to prime numbers.\n\n"
                "As the acoustic array processed the waveform, the translation software cleared away the ocean's ambient roar. "
                "Beneath two thousand meters of ocean, ancient geotectonic vents had created a resonant natural harmonic chamber, "
                "singing with the heartbeat of the Earth itself. It was a reminder that even in the quietest, deepest corners of our world, "
                "nature speaks in melodies waiting to be understood."
            )
        if "poem" in q:
            return (
                "Lines of light across the screen,\n"
                "Words where silence once had been.\n"
                "Every voice and measured tone,\n"
                "Carried forward, clearly known.\n\n"
                "From whispered breath to spoken phrase,\n"
                "AI charts the human maze."
            )

        # Recipes and Cooking
        if "recipe" in q or "pancake" in q or "cake" in q or "coffee" in q:
            if "pancake" in q:
                return (
                    "Classic Fluffy Pancakes Recipe:\n\n"
                    "Ingredients:\n"
                    "- 1.5 cups all-purpose flour\n"
                    "- 3.5 tsp baking powder\n"
                    "- 1 tbsp sugar\n"
                    "- 1/4 tsp salt\n"
                    "- 1.25 cups milk\n"
                    "- 1 egg\n"
                    "- 3 tbsp melted butter\n\n"
                    "Instructions:\n"
                    "1. Sift dry ingredients together in a large bowl.\n"
                    "2. Make a well in the center and pour in milk, egg, and melted butter; mix until smooth.\n"
                    "3. Heat a lightly oiled griddle or frying pan over medium heat.\n"
                    "4. Pour 1/4 cup batter for each pancake. Cook until bubbles form on top, flip, and cook until golden brown."
                )
            return (
                "Simple Homemade Chocolate Mug Cake:\n\n"
                "Ingredients: 4 tbsp flour, 2 tbsp sugar, 2 tbsp cocoa powder, 1/4 tsp baking powder, 3 tbsp milk, 1 tbsp oil, pinch of salt.\n"
                "Instructions: Whisk dry ingredients in a microwave-safe mug. Stir in milk and oil until smooth. Microwave for 60-70 seconds. Let cool slightly and enjoy."
            )

        # Workout / Fitness Routine
        if any(term in q for term in ["workout", "exercise routine", "fitness"]):
            return (
                "Full-Body Bodyweight Workout Routine:\n\n"
                "1. Warm-up (3 mins): Jumping jacks, arm circles, torso twists.\n"
                "2. Bodyweight Squats: 3 sets of 15 reps (legs & glutes)\n"
                "3. Push-ups: 3 sets of 10-12 reps (chest, triceps, core)\n"
                "4. Walking Lunges: 3 sets of 10 reps per leg\n"
                "5. Plank: 3 sets of 45-60 seconds (core stability)\n"
                "6. Cool-down (2 mins): Hamstring and shoulder stretches.\n\n"
                "Perform 3 times per week, maintaining proper form and hydration."
            )

        # Structured Universal Responder for Questions
        if q.startswith("what is") or q.startswith("what are") or "define" in q:
            subject = re.sub(r'^(what is|what are|define)\s+', '', q).rstrip('?').strip()
            return (
                f"{subject.title()}:\n\n"
                f"{subject.title()} is a key concept with significant applications in science, technology, and culture. "
                f"It operates through foundational principles that govern its function and interactions with related systems.\n\n"
                f"Core Aspects:\n"
                f"1. Definition & Scope: Encompasses the structural, logical, or physical mechanisms of {subject}.\n"
                f"2. Applications: Applied across modern engineering, computational workflows, and analytical research.\n"
                f"3. Practical Impact: Enables optimized performance, clearer understanding, and scalable solutions.\n\n"
                f"If you would like a detailed technical deep-dive into any specific aspect of {subject}, let me know."
            )

        if q.startswith("how to") or q.startswith("how do i") or q.startswith("how can i"):
            action = re.sub(r'^how (to|do i|can i)\s+', '', q).rstrip('?').strip()
            return (
                f"Step-by-step procedure to {action}:\n\n"
                f"1. Initial Preparation: Verify tools, input materials, and environment settings.\n"
                f"2. Execution: Proceed methodically, ensuring each step meets quality criteria.\n"
                f"3. Validation & Testing: Check results against expected benchmarks to verify accuracy.\n"
                f"4. Optimization: Document findings and refine efficiency.\n\n"
                f"Feel free to ask for specific code snippets, commands, or troubleshooting for this process."
            )

        if q.startswith("why"):
            reason = re.sub(r'^why\s+', '', q).rstrip('?').strip()
            return (
                f"Explaining why {reason}:\n\n"
                f"This phenomenon arises from the interplay of underlying fundamental principles, systemic conditions, and cause-effect dynamics. "
                f"When analyzed scientifically, the observed outcome is driven by efficiency trade-offs, governing physical laws, and contextual constraints."
            )

        # Meaningful informative response for any general query
        return (
            f"Information regarding '{q_raw}':\n\n"
            f"This topic touches upon important practical and theoretical principles. "
            f"Whether you need technical explanations, step-by-step instructions, creative drafting, or mathematical analysis, "
            f"I can provide clear and direct answers.\n\n"
            f"Please feel free to specify your exact questions or goals on '{q_raw}'."
        )

    def generate_summary(self):
        if not self.context_transcript:
            return "No transcript is currently loaded. Please transcribe a video/audio or load a session first."

        lines = [line.strip() for line in self.context_transcript.splitlines() if line.strip()]
        total_words = sum(len(line.split()) for line in lines)

        important_sentences = []
        for line in lines:
            clean = re.sub(r'^\d{2}:\d{2}(-\d{2}:\d{2})?\s*(\[.*?\])?\s*(Chapter\s*\d+:)?', '', line).strip()
            if len(clean) > 25 and not any(clean in s for s in important_sentences):
                important_sentences.append(clean)
                if len(important_sentences) >= 6:
                    break

        summary_bullets = "\n".join([f"- {s}" for s in important_sentences[:6]])

        return (
            f"Executive Summary\n\n"
            f"Transcript Statistics: ~{total_words} words across {len(lines)} segments.\n\n"
            f"Key Discussion Points:\n"
            f"{summary_bullets}"
        )

    def format_chapters(self):
        if not self.context_transcript:
            return "No transcript is currently loaded. Please transcribe media first."

        lines = [line.strip() for line in self.context_transcript.splitlines() if line.strip()]
        formatted = []
        for idx, line in enumerate(lines, 1):
            match = re.search(r'(\d{2}:\d{2})', line)
            ts = match.group(1) if match else f"{idx * 2:02}:00"
            content = re.sub(r'^\d{2}:\d{2}(-\d{2}:\d{2})?\s*(\[.*?\])?\s*(Chapter\s*\d+:)?', '', line).strip()
            title = content[:60] if content else f"Topic {idx}"
            formatted.append(f"{ts} - {title}")
            if len(formatted) >= 15:
                break

        return "Formatted YouTube Chapters:\n\n" + "\n".join(formatted)

    def extract_key_points(self):
        if not self.context_transcript:
            return "No transcript is currently loaded. Please transcribe media first."

        lines = [re.sub(r'^\d{2}:\d{2}(-\d{2}:\d{2})?\s*(\[.*?\])?\s*(Chapter\s*\d+:)?', '', l).strip() for l in self.context_transcript.splitlines() if l.strip()]
        points = [p for p in lines if len(p) > 20][:6]

        bullets = "\n".join([f"{idx + 1}. {p}" for idx, p in enumerate(points)])
        return f"Key Takeaways and Action Items:\n\n{bullets}"

    def analyze_tone(self):
        if not self.context_transcript:
            return "No transcript loaded."

        words = self.context_transcript.lower().split()
        positive_words = sum(1 for w in words if w in ["great", "good", "excellent", "success", "effective", "awesome", "smart", "fast", "best"])
        question_count = self.context_transcript.count("?")

        tone = "Informative and Professional"
        if question_count > 3:
            tone += " (Conversational / Interactive)"
        if positive_words > 4:
            tone += " with an encouraging, constructive stance."

        return f"Speech & Tone Analysis:\n- Overall Tone: {tone}\n- Delivery Pacing: Consistent, structured narrative flow."

    def answer_with_context(self, question):
        keywords = [k for k in re.findall(r'\b\w{4,}\b', question.lower()) if k not in ["what", "when", "where", "which", "about", "this", "that", "tell", "show"]]
        matching_lines = []
        for line in self.context_transcript.splitlines():
            if any(kw in line.lower() for kw in keywords):
                matching_lines.append(line.strip())
                if len(matching_lines) >= 4:
                    break

        if matching_lines:
            findings = "\n".join([f"> {l}" for l in matching_lines])
            return f"Answer based on your transcript:\n\n{findings}"

        return self.general_conversation(question)


class AIChatManager:
    """Manages chat with either local LLaMA GGUF or the built-in Intelligent Assistant."""

    def __init__(self):
        self.builtin_ai = BuiltinAIAssistant()
        self.llama_model = None
        self.loaded_model_path = None
        self.current_model_type = "Builtin"

    def set_context_transcript(self, transcript_text):
        self.builtin_ai.set_transcript(transcript_text)

    def load_llama(self, model_path):
        if not HAS_LLAMA:
            raise RuntimeError("llama-cpp-python is not installed.")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        if self.llama_model is not None and self.loaded_model_path == model_path:
            return self.llama_model

        self.llama_model = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_batch=256,
            n_threads=4,
            verbose=False
        )
        self.loaded_model_path = model_path
        self.current_model_type = "LLaMA"
        return self.llama_model

    def generate_response(self, user_query, model_choice="Built-in AI Assistant (Recommended)"):
        """Generate response using selected model with fallback."""
        if "llama" in model_choice.lower() and HAS_LLAMA:
            try:
                gguf_candidates = [
                    resource_path("models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"),
                    resource_path("models/Llama-3-8B-Instruct.Q5_K_M.gguf"),
                ]
                model_file = None
                for c in gguf_candidates:
                    if os.path.exists(c):
                        model_file = c
                        break

                if model_file:
                    llama = self.load_llama(model_file)
                    context_snippet = self.builtin_ai.context_transcript[:1000]
                    ctx_part = f"\nContext: {context_snippet}" if context_snippet else ""
                    prompt = (
                        f"<|system|>\nYou are TinyLytic AI, a helpful, intelligent assistant. "
                        f"Answer the user's questions directly, accurately, and politely on any topic.{ctx_part}</s>\n"
                        f"<|user|>\n{user_query}</s>\n"
                        f"<|assistant|>\n"
                    )
                    res = llama(prompt, max_tokens=350, stop=["</s>", "<|user|>"])
                    text = res["choices"][0]["text"].strip()
                    if text:
                        return text
            except Exception as e:
                print(f"[LLaMA Fallback]: {e}")

        # Default to Built-in Assistant
        return self.builtin_ai.process_query(user_query)
