"""Encouragement message bank with a no-repeat rotation.

Messages are keyed by (domain, level, event) and written like a musician
talking to a student: each names the concept or skill it celebrates, so it
teaches while it encourages. No empty hype, no recycled lines.

Events
------
correct_streak       several right answers in a row inside a session
lesson_complete      a 10-exercise lesson finished
level_up             a domain's overall level crossed into the next band
comeback_after_miss  first correct answer right after a miss
mastery              a skill crossed the mastery threshold
daily_goal           today's XP goal reached

No-repeat guarantee
-------------------
Used variant indices persist per bucket in the kv table (``fbmsg.<domain>.
<level>.<event>``). A variant is excluded until the bucket is exhausted, then
the bucket reshuffles, still avoiding back-to-back repetition. The store is
plain JSON via Database.kv_get/kv_set: no new tables, no schema change.

Messages may use ``{skill}``, ``{level}``, ``{domain}`` and ``{streak}``
placeholders; missing values degrade to a generic word, never a KeyError.
"""

from __future__ import annotations

import random

DOMAINS = ("theory", "aural", "piano")
EVENTS = ("correct_streak", "lesson_complete", "level_up",
          "comeback_after_miss", "mastery", "daily_goal")

# LEVEL_ORDER from curriculum.model, repeated here to avoid an import cycle;
# test_feedback_messages cross-checks the two stay identical.
LEVELS = ("Beginner", "Early", "Intermediate", "Advanced", "Graduate")


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - trivial
        return {"skill": "this skill", "level": "the next level",
                "domain": "music", "streak": "several"}.get(key, "")


def pick_message(db, domain: str, level: str, event: str, /, **fmt) -> str:
    """Return the next unused variant for the bucket, never repeating until
    every variant has been shown, and never showing the same line twice in a
    row across a reshuffle."""
    variants = _bucket(domain, level, event)
    if not variants:
        return ""
    key = f"fbmsg.{domain}.{level}.{event}"
    used = db.kv_get(key, [])
    if not isinstance(used, list):
        used = []
    used = [i for i in used if isinstance(i, int) and 0 <= i < len(variants)]
    unused = [i for i in range(len(variants)) if i not in used]
    if not unused:
        last = used[-1] if used else -1
        used = []
        unused = [i for i in range(len(variants)) if i != last] or [last]
    idx = random.choice(unused)
    used.append(idx)
    db.kv_set(key, used)
    return variants[idx].format_map(_SafeDict(fmt))


def _bucket(domain: str, level: str, event: str) -> list[str]:
    """Resolve the most specific bucket available."""
    for key in ((domain, level, event), (domain, "any", event),
                ("any", level, event), ("any", "any", event)):
        if key in MESSAGES:
            return MESSAGES[key]
    return []


def variants_for(domain: str, level: str, event: str) -> list[str]:
    """Test/inspection helper: the variants pick_message would draw from."""
    return list(_bucket(domain, level, event))


# ---------------------------------------------------------------------------
# The bank. Keep each line useful: name the concept, the skill, or the habit.
# House style: plain sentences, no em dashes, no exclamation stacking, no
# inflated praise words. Vary sentence shape across a bucket.
# ---------------------------------------------------------------------------

MESSAGES: dict[tuple[str, str, str], list[str]] = {
    # Filled in below; see the per-domain sections.
}

# -- generic fallbacks (used only if a specific bucket is missing) ----------
MESSAGES[("any", "any", "correct_streak")] = [
    "{streak} in a row. The pattern is settling in.",
    "That run of {streak} was no accident. Keep the thread going.",
    "A clean streak of {streak}. Accuracy first, speed follows.",
    "{streak} straight. You answered before doubt got a vote.",
    "Another one lands. That makes {streak} without a miss.",
    "{streak} consecutive correct. This is what fluency feels like early on.",
    "The streak is at {streak}. Notice how much less you hesitate now.",
    "Still perfect after {streak}. Your guesses stopped being guesses.",
]
MESSAGES[("any", "any", "lesson_complete")] = [
    "Lesson done. {skill} is a little more yours than it was ten minutes ago.",
    "That wraps the set. Every rep on {skill} compounds.",
    "Ten exercises down. {skill} will load faster next time you see it.",
    "Lesson complete. The next review of {skill} will tell us what stuck.",
    "Done. You just bought future-you a head start on {skill}.",
    "Set finished. Sleep will do the filing on {skill} tonight.",
    "That is the lesson. Short, focused work like this beats cramming.",
    "Complete. {skill} moves from new to familiar through exactly this.",
]
MESSAGES[("any", "any", "level_up")] = [
    "Level up. {domain} now sits at {level}.",
    "{domain} just crossed into {level}. The material will stretch you a bit more from here.",
    "New band reached: {level} in {domain}. Earned, not given.",
    "Your {domain} work is now {level}. The fundamentals held.",
    "{level}. That is the new floor for your {domain} skills, not the ceiling.",
    "Promotion: {domain} is {level} now. Expect meatier exercises.",
    "The {domain} dial moved to {level}. Consistency did that.",
    "{domain}: {level}. Keep showing up and the next band follows.",
]
MESSAGES[("any", "any", "comeback_after_miss")] = [
    "Good correction. The miss showed you the edge of the rule, and you found it.",
    "Right back on it. Misses mark exactly where learning happens.",
    "Recovered. One wrong answer is information, two would be a pattern.",
    "That is the bounce-back. You adjusted instead of guessing again.",
    "Nice reset. You read the feedback and used it.",
    "Back on track. The brain encodes corrections more deeply than easy wins.",
    "There it is. An error followed by a fix is a full learning cycle.",
    "Corrected. That is the whole job: miss, understand, adjust.",
]
MESSAGES[("any", "any", "mastery")] = [
    "{skill} is mastered. It will come back occasionally so it stays that way.",
    "Mastered: {skill}. From here it is maintenance, not study.",
    "{skill} just crossed the mastery line. The reviews ahead are insurance.",
    "That settles {skill}. New material unlocks from this foundation.",
    "{skill}: mastered. You can now lean on it while learning what comes next.",
    "Mastery on {skill}. The spaced reviews will keep it warm.",
    "{skill} goes in the solved column. It took exactly the reps it took.",
    "Confirmed mastery of {skill}. Quietly one of the best moments in practice.",
]
MESSAGES[("any", "any", "daily_goal")] = [
    "Daily goal met. The streak math only works when today happens, and it did.",
    "Goal reached for today. Frequency beats heroics in skill learning.",
    "That is today's goal. A short session done daily outperforms a long one done rarely.",
    "Daily goal complete. Tomorrow starts from a slightly higher floor.",
    "Done for the day, if you want to be. Everything past this point is bonus.",
    "Goal hit. The habit is the real achievement; the XP is just the receipt.",
    "Today's quota is in. Consistency is the only technique that works for everyone.",
    "Daily goal cleared. Small daily deposits, compounding interest.",
]

# ===========================================================================
# theory
# ===========================================================================

# -- theory / Beginner: note names, the staff, clefs, accidentals, steps ----
MESSAGES[("theory", "Beginner", "correct_streak")] = [
    "{streak} notes named without a miss. The staff is turning into a map you can read at a glance.",
    "That's {streak} in a row. Treble and bass clef are starting to feel like one keyboard, not two puzzles.",
    "{streak} straight. You're reading line and space positions, not counting up from middle C every time.",
    "A streak of {streak}. Sharps and flats stopped slowing you down somewhere around the third one.",
    "{streak} correct. Half steps and whole steps are becoming something you see, not something you compute.",
    "No misses in {streak}. Ledger lines used to be the hard part, and you just read straight through them.",
    "{streak} in a row says the note names are moving into long-term storage.",
    "Clean run of {streak}. Reading pitch this fast is the foundation every later skill sits on.",
]
MESSAGES[("theory", "Beginner", "lesson_complete")] = [
    "{skill} done. Every chord and scale you ever learn will be spelled with the notes you just practiced.",
    "Lesson finished. The staff has eleven positions per clef, and you are starting to own all of them.",
    "That wraps {skill}. Next time a note sits on a ledger line, it will look less like a mystery.",
    "Set complete. Accidentals raise or lower by a half step, and now your eye catches them on the way in.",
    "{skill} is in the books. Note reading is the alphabet here, and you just finished a page of it.",
    "Done. The distance from E to F is a half step, and you knew it without checking. Progress.",
    "Lesson complete. Reading both clefs is what lets you see the whole grand staff as one instrument.",
    "{skill} wrapped up. The faster these notes load, the more attention you can spend on the music itself.",
]
MESSAGES[("theory", "Beginner", "level_up")] = [
    "{level} reached. Note names and the staff held up, so scales and key signatures are next.",
    "You just crossed into {level}. The musical alphabet is yours; now we start arranging it into keys.",
    "New band: {level}. Whole steps and half steps were the warm-up for building real scales.",
    "Theory moves to {level}. Reading notes was step one; relating them to each other is step two.",
    "{level} now. From here the staff stops being the subject and starts being the tool.",
    "Welcome to {level}. You can name what you see; soon you will name why it sounds the way it does.",
    "Level up to {level}. Accidentals behaved, ledger lines behaved, and the next material builds on both.",
    "Theory is at {level}. Keys, scales, and intervals all assume the reading you just proved.",
]
MESSAGES[("theory", "Beginner", "comeback_after_miss")] = [
    "Good fix. Most early misses are clef confusion, and you sorted out which staff you were on.",
    "Back on track. A flat lowers, a sharp raises; the miss made the rule stick harder.",
    "There it is. You recounted the lines and spaces instead of guessing, and that is the right habit.",
    "Recovered. B to C is a half step with no black key between, and now you have felt why that matters.",
    "Nice correction. One wrong note name is how everyone learns the staff. Twice is rare after a fix like that.",
    "Right answer. Reading from the clef sign first, then the position, is exactly what straightened it out.",
    "Solid recovery. The natural sign cancels the accidental; that catch will save you for years.",
    "Corrected. Ledger lines just continue the staff pattern, and you proved you can extend it.",
]
MESSAGES[("theory", "Beginner", "mastery")] = [
    "{skill} is mastered. You read both clefs the way you read words, and that never goes away.",
    "Mastery on {skill}. Every interval, chord, and key signature ahead is built from these note names.",
    "{skill}: mastered. Half steps, whole steps, and accidentals are now reflexes, not calculations.",
    "That settles {skill}. The grand staff is officially familiar territory.",
    "{skill} crosses the line. Music notation just became a language you are literate in.",
    "Mastered: {skill}. When scale spelling shows up, the alphabet will already be automatic.",
    "{skill} is done for good, with occasional reviews to keep it polished. The staff is home now.",
    "Confirmed: {skill}. The slowest part of reading music is gone from your process.",
]
MESSAGES[("theory", "Beginner", "daily_goal")] = [
    "Daily goal met. A few minutes of note reading every day beats an hour once a week.",
    "Goal reached. The staff rewards daily eyes on it; recognition speed grows in your sleep.",
    "Today's work is in. Note names are pure recall, and recall is built by exactly this kind of repetition.",
    "That's the goal for today. Tomorrow the same notes will load a little faster.",
    "Daily goal done. At this stage, showing up is most of the curriculum.",
    "Goal complete. Beginning theory is brick-laying, and you set today's bricks.",
    "Done for today. The reading fluency you want in a month is being purchased right now.",
    "Daily goal hit. Keep the streak alive and the fundamentals will carry everything later.",
]

# -- theory / Early: major scales, key signatures, intervals, triads -------
MESSAGES[("theory", "Early", "correct_streak")] = [
    "{streak} in a row. The circle of fifths is turning from a chart into a mental shortcut.",
    "That run of {streak} says interval quality is clicking. Major, minor, perfect, all sorted fast.",
    "{streak} straight. Key signatures are starting to announce their key before you count sharps.",
    "A streak of {streak}. Scale spelling is mostly pattern now, whole and half steps in the right slots.",
    "{streak} without a miss. Triads are reading as stacked thirds, not three separate notes.",
    "Clean {streak}. You see the logic now: every major key uses the same step pattern from a new home.",
    "{streak} correct answers. The last sharp points to the leading tone, and you clearly know it.",
    "Streak at {streak}. Quality plus number names any interval, and you are naming them on sight.",
]
MESSAGES[("theory", "Early", "lesson_complete")] = [
    "{skill} finished. Each major scale is the same recipe from a new starting note, and you just baked another batch.",
    "Lesson done. Key signatures are the spelling rules of a key, and yours are getting reliable.",
    "That completes {skill}. Intervals are the rulers of music; everything else gets measured with them.",
    "Set done. A major triad is a major third with a minor third on top, and that fact just got cheaper to recall.",
    "{skill} wrapped. The circle of fifths organizes all twelve keys, and you walked another arc of it.",
    "Done. Spelling triads in flat keys takes more care, and you gave it that care.",
    "Lesson complete. Once intervals are automatic, chords are just intervals wearing a coat.",
    "{skill} in the books. F sharp and G flat are the same key with different paperwork, and you can do the paperwork.",
]
MESSAGES[("theory", "Early", "level_up")] = [
    "{level} unlocked. Scales and intervals held steady, so chords and harmony come next.",
    "Theory is {level} now. The circle of fifths got you here; Roman numerals will take it from here.",
    "New level: {level}. You can spell what a key contains. Soon you will track what a key does.",
    "{level}. Interval quality was the gatekeeper skill, and you got past it honestly.",
    "Welcome to {level}. Triads in root position are settled; inversions and sevenths are waiting.",
    "Level up: {level}. Major keys behave for you now, which is exactly when minor keys get interesting.",
    "Crossed into {level}. The materials of tonal music are in your hands; next comes how they move.",
    "{level} reached. Every key signature you drilled is about to pay rent in harmonic analysis.",
]
MESSAGES[("theory", "Early", "comeback_after_miss")] = [
    "Good catch. A sixth inverts to a third; once you flipped it, the quality fell into place.",
    "Recovered. Counting the half steps settles any interval argument, and you settled it.",
    "Back in it. The order of sharps never changes, F C G D A E B, and now it is one miss deeper in your memory.",
    "Nice fix. Augmented and diminished live one half step past major and minor, and you found the line.",
    "Corrected. Scale spelling needs one of each letter name; that rule just earned its keep.",
    "Right answer. Relative major and minor share a signature, and the miss showed you which one was asking.",
    "There is the adjustment. A triad's quality lives in its thirds, and you went back and measured them.",
    "Good recovery. Flat keys grow by fourths; you retraced the circle and landed it.",
]
MESSAGES[("theory", "Early", "mastery")] = [
    "{skill} mastered. Twelve keys, one pattern, zero hesitation.",
    "Mastery: {skill}. Intervals are now a measuring tool you own rather than a topic you study.",
    "{skill} crosses the threshold. Chord spelling ahead will lean on this constantly.",
    "That locks in {skill}. The circle of fifths is now part of how you think, not something you consult.",
    "Mastered: {skill}. Quality and number, instantly, in any clef. That is the whole assignment.",
    "{skill} is settled. Harmony is intervals in motion, and your intervals are ready to move.",
    "Mastery reached on {skill}. Key signatures will never again be the slow part of a problem.",
    "{skill}: done and durable. Reviews will visit occasionally, like a tuner checking a good piano.",
]
MESSAGES[("theory", "Early", "daily_goal")] = [
    "Daily goal reached. Scales and intervals are memory skills, and memory is built on schedule.",
    "Goal met. A daily pass through the keys keeps the whole circle warm.",
    "Today's theory is done. Interval fluency is bought in small daily payments, and you paid one.",
    "Goal complete. Each session, the gap between seeing and knowing shrinks a little.",
    "That is the day's goal. Key signatures love routine more than talent.",
    "Daily target hit. You are at the stage where consistency converts directly into speed.",
    "Done for today. The spacing between sessions is doing half the teaching.",
    "Goal in. Come back tomorrow and the fourths and fifths will be waiting, slightly easier.",
]

# -- theory / Intermediate: minor keys, modes, sevenths, figures, numerals -
MESSAGES[("theory", "Intermediate", "correct_streak")] = [
    "{streak} in a row. Roman numerals are starting to read like sentences instead of symbols.",
    "Streak of {streak}. You are telling half-diminished from fully diminished without a second look.",
    "{streak} straight. Figured bass is turning into shapes: 6 means first inversion before you even think.",
    "A run of {streak}. The three minor scale forms are sorting themselves, raised sixth and seventh on demand.",
    "{streak} correct. Dominant seventh versus major seventh is a one-glance call for you now.",
    "Clean streak, {streak} deep. You see the function behind each numeral, not just the label.",
    "{streak} in a row on chords this thick. Sevenths add one more third to the stack, and you stack fast.",
    "That makes {streak}. Modes used to be a lookup table; now they are flavors you recognize.",
]
MESSAGES[("theory", "Intermediate", "lesson_complete")] = [
    "{skill} complete. Roman numerals say what a chord does in a key, and you are starting to read the plot.",
    "Lesson done. Inversions change the bass, not the chord, and that idea is settling in.",
    "{skill} finished. Harmonic minor exists so V can be major; the raised seventh is the whole story.",
    "That wraps {skill}. Seventh chords come in five qualities, and you can now build most of them cold.",
    "Set done. Figured bass is shorthand from the 1600s, and you just got more fluent in it than most pianists.",
    "{skill} done. ii to V to I is the most traveled road in tonal music, and you mapped it again.",
    "Lesson complete. Each mode is the same notes around a different home, and dorian is finally acting like it.",
    "Done with {skill}. Analysis is slow at first because it is real reading, and you are genuinely reading now.",
]
MESSAGES[("theory", "Intermediate", "level_up")] = [
    "Theory hits {level}. Roman numerals stopped being labels and started being a way of seeing harmony whole.",
    "{level} reached. Diatonic harmony is under your belt; chromatic chords are next, and they are the fun ones.",
    "New level: {level}. Sevenths and inversions behaved, so secondary dominants are about to introduce themselves.",
    "Welcome to {level}. You analyze in numerals now; soon you will follow music as it leaves its home key.",
    "{level}. Figured bass, modes, and minor keys all checked out. Voice leading is where they start to sing.",
    "Level up to {level}. The vocabulary phase is ending; the grammar phase, how chords connect, begins.",
    "Theory is {level} now. Borrowed chords and tonicization will bend the rules you just earned.",
    "{level} unlocked. You can name every diatonic chord; next you learn the ones that visit from other keys.",
]
MESSAGES[("theory", "Intermediate", "comeback_after_miss")] = [
    "Good fix. The seventh resolves down by step; once you tracked it, the chord identified itself.",
    "Recovered. In minor, check the seventh scale degree first. Raised means dominant function, and you caught it.",
    "Back on it. A 6/4 means second inversion, fifth in the bass. The figure told you once you asked.",
    "Nice correction. Quality of the triad plus quality of the seventh: two checks, and you ran both the second time.",
    "Right answer. Mode questions come down to where the half steps fall, and you went looking for them.",
    "Corrected. The numeral's case carries the quality, lowercase for minor, and that detail just got permanent.",
    "There is the recovery. You spelled the chord from the bass up instead of trusting the top note. That is the move.",
    "Good adjustment. The leading-tone triad is diminished, not minor; one miss there buys a lifetime of remembering.",
]
MESSAGES[("theory", "Intermediate", "mastery")] = [
    "{skill} mastered. You read harmony in functions now, and that changes how every score looks.",
    "Mastery on {skill}. Five seventh-chord qualities, instantly sorted. Jazz charts just got easier too.",
    "{skill}: mastered. Inversions are bass management, and your bass-line awareness is now permanent gear.",
    "That settles {skill}. Minor keys with their movable sixth and seventh degrees no longer rattle you.",
    "Mastered: {skill}. Roman numerals are how theorists gossip about chords, and you are fluent.",
    "{skill} locked in. Chromatic harmony assumes everything you just proved, and you are ready for it.",
    "Mastery: {skill}. Figured bass went from antique notation to a tool you actually use.",
    "{skill} is mastered. Analysis speed comes from chunking, and you are chunking whole progressions now.",
]
MESSAGES[("theory", "Intermediate", "daily_goal")] = [
    "Daily goal met. Analysis is a craft skill; daily contact is how the chunks form.",
    "Goal done. Ten minutes with Roman numerals today outweighs a binge on Sunday.",
    "Today's goal is in. Seventh chords settle through spaced returns, and you just made one.",
    "Goal reached. Harmony study compounds: every session makes the next progression more readable.",
    "That is the day. The minor-key details stay sharp only when visited often, and you visited.",
    "Daily goal complete. You kept the streak honest through the hardest stretch of core theory.",
    "Done for the day. Each return visit moves a numeral from worked-out to recognized.",
    "Goal achieved. Mid-level theory is where many students quit; routine is how you will not.",
]

# -- theory / Advanced: secondary dominants, mixture, modulation, leading --
MESSAGES[("theory", "Advanced", "correct_streak")] = [
    "{streak} in a row through chromatic territory. Secondary dominants read as arrows now, not anomalies.",
    "Streak of {streak}. You spot the borrowed chords: mixture is just minor lending a color to major.",
    "{streak} straight. Augmented sixths resolve outward to the dominant, and you see it coming.",
    "{streak} without a miss. V of V no longer looks like a wrong note; it looks like intent.",
    "A run of {streak}. You track modulations by pivot chord instead of noticing them three bars late.",
    "Clean {streak}. The Neapolitan in first inversion, flat side and proud, and you call it instantly.",
    "{streak} correct. Voice-leading logic is doing the work: tendency tones are pulling and you feel the pull.",
    "{streak} in a row at this level is real analysis, the kind that holds up in a seminar.",
]
MESSAGES[("theory", "Advanced", "lesson_complete")] = [
    "{skill} complete. A secondary dominant tonicizes its target for one moment, and you can see the lean.",
    "Lesson done. Modulation is a change of address; the pivot chord is the moving van, and you found it.",
    "{skill} finished. The German sixth sounds like a dominant seventh until it resolves, and you kept them straight.",
    "That wraps {skill}. Mixture chords borrow from the parallel minor, and you are cataloging the loans.",
    "Set complete. Good voice leading is mostly steps and common tones; you practiced restraint, the hard skill.",
    "{skill} done. Chromaticism is the old rules applied to a wider palette, and you applied them.",
    "Lesson finished. Every altered chord here still resolves by half-step logic, and you traced the resolutions.",
    "{skill} wrapped. This is the harmony of Schubert and Wagner, and you are reading it at speed.",
]
MESSAGES[("theory", "Advanced", "level_up")] = [
    "{level}. Chromatic harmony bowed; post-tonal theory is on the horizon.",
    "Theory reaches {level}. Tonality's edge cases are yours; next come systems beyond tonality.",
    "New level: {level}. You can follow a piece through any modulation; soon keys themselves become optional.",
    "{level} unlocked. The full tonal toolkit, applied chords and all, cleared inspection.",
    "Welcome to {level}. From here, set theory will ask you to measure intervals without a key to lean on.",
    "Level up: {level}. The romantic-era vocabulary is in hand. The twentieth century is next, bring curiosity.",
    "{level} reached. You handle harmony that bends keys. The next material dissolves them entirely.",
    "Theory at {level}. Few students get this far with their fundamentals intact, and yours are.",
]
MESSAGES[("theory", "Advanced", "comeback_after_miss")] = [
    "Good recovery. You asked what the chord resolves to, and the secondary function gave itself away.",
    "Fixed. Italian, French, German: the sixths differ by one interior note, and you went and found it.",
    "Back on track. The Neapolitan wants the bass on the fourth scale degree, and you put it there.",
    "Right answer. Parallel fifths hide in chromatic motion; you slowed down and caught the pair.",
    "Corrected. A modulation is confirmed by a cadence, not a single accidental, and you waited for proof.",
    "There it is. You respelled the enharmonic and the German sixth stopped pretending to be a V7.",
    "Good fix. Borrowed iv still functions as subdominant; the flat third was color, not a new key.",
    "Recovered. Tendency tones do not negotiate. You let the leading tone rise and the answer appeared.",
]
MESSAGES[("theory", "Advanced", "mastery")] = [
    "{skill} mastered. Chromatic chords are part of your thinking now, not exceptions to memorize.",
    "Mastery: {skill}. You can explain why a progression aches, which is the real point of all this.",
    "{skill} crossed the line. Modulation tracking at this level is a professional skill, full stop.",
    "Mastered: {skill}. The nineteenth century's harmony book is open to you cover to cover.",
    "{skill}: mastered. Voice leading is taste backed by rules, and you have internalized both.",
    "That locks {skill}. When set theory arrives, your tonal instincts will be an asset, not a crutch.",
    "Mastery on {skill}. The exotic chords now file themselves under function, where they belong.",
    "{skill} is settled. Analysis at this depth changes how you perform, not just how you label.",
]
MESSAGES[("theory", "Advanced", "daily_goal")] = [
    "Daily goal met. Advanced harmony fades fast without contact; today's session kept it lit.",
    "Goal reached. Chromatic analysis is a muscle, and you trained it on schedule.",
    "Today's goal done. At this level the enemy is rust, and you just sanded some off.",
    "Goal complete. A daily look at hard harmony keeps the pivot-chord reflex alive.",
    "That is the day's work. The graduate material ahead will thank you for this routine.",
    "Daily goal in. You studied the kind of harmony most people only admire from a distance.",
    "Done for today. Deep skills need shallow, frequent maintenance, and that is what this was.",
    "Goal hit. The streak now carries some of the densest material in the curriculum.",
]

# -- theory / Graduate: pc sets, vectors, rows, transforms, Tonnetz --------
MESSAGES[("theory", "Graduate", "correct_streak")] = [
    "{streak} in a row. Normal form is becoming a rotation you see, not a procedure you run.",
    "Streak of {streak}. You are reading interval vectors like nutrition labels for sonorities.",
    "{streak} straight. Prime form, packed left and transposed to zero, and you get there fast.",
    "{streak} without a miss. Row forms snap into place: P, I, R, RI, all one matrix in your head.",
    "A run of {streak}. The L, P, and R transforms feel like moves on a board you know.",
    "Clean {streak}. You treat pitch classes mod 12 without translating back to note names first.",
    "{streak} correct. Forte names are attaching to actual sounds now, not just to digit strings.",
    "{streak} in a row at the graduate level. This is fluency in the field's working language.",
]
MESSAGES[("theory", "Graduate", "lesson_complete")] = [
    "{skill} complete. Normal form is just the tightest packing of a set, and your packing is getting quick.",
    "Lesson done. The interval vector counts every interval class inside a set, and you are reading the counts.",
    "{skill} finished. Twelve-tone rows guarantee all twelve tones; the art is in the ordering, and you tracked it.",
    "That wraps {skill}. A single PLR move connects triads that share two tones, and you traced the voice leading.",
    "Set finished, in both senses. Prime form lets any two collections be compared, and you compared them.",
    "{skill} done. Tn slides a set, TnI flips it first, and you kept the two operations straight.",
    "Lesson complete. Forte's catalog gives every set class a name, and you are learning the neighborhood.",
    "{skill} wrapped. Post-tonal analysis rewards exactness, and your answers were exact.",
]
MESSAGES[("theory", "Graduate", "level_up")] = [
    "{level}. The whole map, from note names to set classes, is now territory you have walked.",
    "Theory reaches {level}. You operate in systems where the octave has twelve equal citizens.",
    "{level} confirmed. Atonal vocabulary held up under drilling, which is the only way it holds at all.",
    "Welcome to {level}. From Forte numbers to hexachordal thinking, you are inside the discipline now.",
    "New level: {level}. This is coursework-grade fluency, the kind comprehensive exams ask about.",
    "{level} reached. The matrix and the Tonnetz both answered to you. The literature is open.",
    "Level up: {level}. You now analyze music that abandoned keys, with tools built for exactly that.",
    "{level}. Beyond this point, progress is measured in papers read and pieces analyzed. You are equipped.",
]
MESSAGES[("theory", "Graduate", "comeback_after_miss")] = [
    "Good fix. You rechecked the packing from the right, and the normal form sorted itself out.",
    "Recovered. Inversion before transposition: TnI order matters, and now it is burned in.",
    "Back on it. You recounted the interval classes and the vector confessed.",
    "Corrected. Retrograde inversion reads the inversion backward, and you walked the row again to prove it.",
    "Right answer. The best normal order broke the tie at the second interval, and you went back to check it.",
    "There is the recovery. Mod 12 arithmetic forgives nothing, and you stopped rounding corners.",
    "Good correction. The R transform keeps the shared third; you traced which tones held still.",
    "Fixed. Set-class membership survives transposition and inversion, and your second look used that.",
]
MESSAGES[("theory", "Graduate", "mastery")] = [
    "{skill} mastered. You hold a tool most musicians never even meet, and you can use it cold.",
    "Mastery: {skill}. Prime forms surface instantly now, which makes real analysis possible at reading speed.",
    "{skill}: mastered. The twelve-tone machinery is yours; Webern will still surprise you, but not confuse you.",
    "Mastered: {skill}. The Tonnetz is now a place you navigate rather than a diagram you saw once.",
    "That locks {skill}. Interval-class thinking has joined your permanent analytical kit.",
    "{skill} crossed the threshold. This is the level where you could explain it to a seminar, cold.",
    "Mastery on {skill}. The notation is dense, the idea is clean, and you own both now.",
    "{skill} settled. From here, the skill grows by reading scores, and you have the keys.",
]
MESSAGES[("theory", "Graduate", "daily_goal")] = [
    "Daily goal met. Set theory stays sharp the same way counterpoint does: regular, modest doses.",
    "Goal done. You did graduate drill work today, the unglamorous kind that makes seminars easy.",
    "Today's goal reached. Matrix fluency survives on maintenance, and you paid the bill.",
    "Goal complete. Even at this level, the spacing effect is the strongest tool in the room.",
    "That is the day. Most doctoral students cram this material; you are spacing it, which is smarter.",
    "Daily goal in. The abstract material decays fastest, and today's session pushed the decay back.",
    "Done for today. A daily touch on post-tonal skills keeps the whole edifice load-bearing.",
    "Goal hit. The streak now includes twelve-tone arithmetic, which is a sentence few people can say.",
]

# ===========================================================================
# aural
# ===========================================================================

# -- aural / Beginner: interval recognition, short melodic and rhythmic ----
MESSAGES[("aural", "Beginner", "correct_streak")] = [
    "{streak} in a row. Your ear is sorting steps from leaps without asking your eyes for help.",
    "Streak of {streak}. The octave's open ring and the fifth's hollow calm are becoming old friends.",
    "{streak} straight. You are catching melodies in two-note chunks instead of one note at a time.",
    "{streak} correct by ear alone. That is the skill: no staff, no keyboard, just listening.",
    "A run of {streak}. Long versus short note values are landing in the right boxes now.",
    "Clean {streak}. The minor second's crunch is unmistakable to you already.",
    "{streak} in a row. You are starting to hold a melody in memory long enough to write it down.",
    "{streak} without a miss. Hearing came before notation historically, and your training agrees.",
]
MESSAGES[("aural", "Beginner", "lesson_complete")] = [
    "{skill} complete. Each interval has a fingerprint, and your ear lifted a few more prints today.",
    "Lesson done. Dictation is memory plus labeling, and both halves got stronger this set.",
    "{skill} finished. The beat is the ruler under every rhythm, and you kept the ruler steady.",
    "That wraps {skill}. You echoed pitches you could not see. That is the whole foundation of musicianship.",
    "Set done. A perfect fourth opens many famous tunes, and now it opens your answers too.",
    "{skill} done. Short patterns first, longer lines later. You are exactly on schedule.",
    "Lesson complete. Your inner ear, the one that hears without sound, just got measurably louder.",
    "{skill} wrapped. Ten listenings, ten judgments. Ears improve only under this kind of pressure.",
]
MESSAGES[("aural", "Beginner", "level_up")] = [
    "{level} by ear. Intervals are sticking, so chords, several notes at once, come next.",
    "Aural skills reach {level}. You hear distances now; soon you will hear qualities and colors.",
    "New level: {level}. From single intervals to whole scales, the listening gets richer from here.",
    "{level} reached. The hardest part of ear training is the start, and the start is behind you.",
    "Welcome to {level}. Your ear graduated from is-it-bigger to what-exactly-is-it.",
    "Level up: {level}. Melodic memory carried you here. Chord quality will test it differently.",
    "{level} now. The dictation phrases get longer, and your ear has earned the extra length.",
    "Aural training hits {level}. Listening is a skill, not a gift, and you just proved it again.",
]
MESSAGES[("aural", "Beginner", "comeback_after_miss")] = [
    "Good ears. You replayed it in your head before answering, and the second hearing told the truth.",
    "Recovered. Fourths and fifths blur for every beginner; you just sharpened the boundary.",
    "Back on it. Singing the interval, even silently, is the fix you found, and it always works.",
    "Right answer. The rhythm was the trap, not the pitch, and you caught which one fooled you.",
    "Corrected. Half steps sound close because they are; your ear now knows exactly how close.",
    "There it is. You anchored to the first note instead of drifting, and the contour came clear.",
    "Nice fix. A miss in dictation usually means memory, not hearing, and you held on longer this time.",
    "Good recovery. Comparing to a song you know is a real technique, and it just paid off.",
]
MESSAGES[("aural", "Beginner", "mastery")] = [
    "{skill} mastered. Your ear identifies what it hears, which is the definition of musicianship.",
    "Mastery: {skill}. These intervals are now permanent residents of your listening.",
    "{skill}: mastered by ear. No chart helped you; that makes it entirely yours.",
    "Mastered: {skill}. Melodies hold still in your memory now, long enough to be written.",
    "That locks {skill}. Rhythm and pitch are separating cleanly when you listen, which is rare this early.",
    "{skill} settled. Every chord you ever name by ear will stand on this interval work.",
    "Mastery on {skill}. You hear like a musician now, and that is not a figure of speech.",
    "{skill} is yours. The inner ear remembers what the outer ear was taught, and yours was taught well.",
]
MESSAGES[("aural", "Beginner", "daily_goal")] = [
    "Daily goal met. Ears improve through daily exposure the way accents form: slowly, then suddenly.",
    "Goal done. Ear training compounds faster than any other musical skill when done daily.",
    "Today's listening is in. Even five focused minutes rewires something.",
    "Goal reached. Your ear got measured against real sounds today, and that is the only test that counts.",
    "That is today's goal. Hearing skills decay quickly when ignored; yours were not ignored.",
    "Daily goal complete. Tomorrow's intervals will sound a little more obvious. That is how it works.",
    "Done for today. You cannot cram an ear; you can only feed it daily, and you fed it.",
    "Goal hit. Listening practice on a streak is the closest thing to a guarantee in music study.",
]

# -- aural / Early: chord quality by ear, scales and modes by ear ----------
MESSAGES[("aural", "Early", "correct_streak")] = [
    "{streak} in a row. Major and minor triads are announcing themselves before you finish listening.",
    "Streak of {streak}. The bright lift of a major third versus the shaded minor: you sort them in real time.",
    "{streak} straight. Diminished chords have that tightened, unsettled sound, and it is not fooling you.",
    "A run of {streak}. You are hearing scales as shapes, where the half steps fall, not note by note.",
    "{streak} correct. Compound intervals are just simple ones with more air, and your ear agrees.",
    "Clean {streak}. The augmented triad's strange symmetry stands right out to you.",
    "{streak} in a row by ear. Quality recognition is pattern recognition, and your patterns are loading.",
    "{streak} and counting. You hear a mode's color before you count its steps. That is the goal.",
]
MESSAGES[("aural", "Early", "lesson_complete")] = [
    "{skill} done. A chord's quality lives in its thirds, and your ear is finally reading the small print.",
    "Lesson complete. Minor keys carry that pull toward darkness, and you tracked it through every example.",
    "{skill} finished. Mixolydian is major with a lowered seventh, and you heard the difference, not just knew it.",
    "That wraps {skill}. Triads arpeggiated or blocked, your ear handled both presentations.",
    "Set done. The harmonic minor's raised seventh leaves an exotic gap, and you caught it by sound.",
    "{skill} complete. Every chord chart you ever hear will be easier because of sets like this one.",
    "Lesson done. You told whole scales apart by their half-step placement alone. Real listening.",
    "{skill} wrapped. Quality by ear is the skill session players rely on every working night.",
]
MESSAGES[("aural", "Early", "level_up")] = [
    "{level} by ear. Chord colors are in; next your ear learns what progressions do with them.",
    "Aural reaches {level}. You hear what a chord is. The coming work asks what it wants.",
    "New level: {level}. Cadences are next, the ear-training equivalent of learning punctuation.",
    "{level} now. Telling modes apart by ear puts you past most undergraduates already.",
    "Welcome to {level}. Single sounds are sorted. Sequences of sounds are the new frontier.",
    "Level up: {level}. Your ear moved from intervals to chords on time and under budget.",
    "{level} reached. The dictations get longer and the harmonies thicker, and you are ready for both.",
    "Aural training hits {level}. The listening so far was vocabulary. Now comes syntax.",
]
MESSAGES[("aural", "Early", "comeback_after_miss")] = [
    "Good fix. Major and minor differ by one half step in the third, and your second listen went straight to it.",
    "Recovered. You let the chord ring before judging, and patience turned out to be the technique.",
    "Back on track. Diminished and minor share a third; the fifth is the tell, and you found the fifth.",
    "Right answer. The mode's lowered seventh slipped past once. It will not slip past often now.",
    "Corrected. Hearing the bass first organizes everything above it, and that is what you did differently.",
    "There it is. You sang the scale back silently and the odd degree exposed itself.",
    "Nice recovery. Wide intervals fool the ear by sounding consonant; you checked the size anyway.",
    "Good ears on the retry. One quality confusion, instantly repaired, is how discrimination sharpens.",
]
MESSAGES[("aural", "Early", "mastery")] = [
    "{skill} mastered. Chord quality by ear is a working musician's tool, and it is now in your kit.",
    "Mastery: {skill}. You hear in colors now: major, minor, and the stranger shades between.",
    "{skill}: mastered. Scales identify themselves to you on first hearing. That used to take a chart.",
    "Mastered: {skill}. The ear work is compounding: chords made sense because intervals did.",
    "That locks {skill}. When harmonic dictation arrives, the chord qualities will already be spoken for.",
    "{skill} settled by ear alone. No visual aid can take credit for this one.",
    "Mastery on {skill}. You recognize sonorities the way you recognize voices on the phone.",
    "{skill} is yours. Listening this precise is built, never born, and you built it.",
]
MESSAGES[("aural", "Early", "daily_goal")] = [
    "Daily goal met. Chord-quality discrimination grows in small daily doses, and today's dose is in.",
    "Goal done. Your ear showed up for work today, which is the entire secret.",
    "Today's listening goal reached. The gap between hearing and naming closed a little more.",
    "Goal complete. Modes and qualities stay vivid only with regular hearings, and you kept the appointment.",
    "That is today's ear work. Frequent short sessions are how discrimination becomes reflex.",
    "Daily goal in. Every day you listen on purpose, your accidental listening improves too.",
    "Done for today. The streak is training your ear even on the days it feels routine.",
    "Goal hit. Daily ears, durable skills. The arithmetic is boring and it absolutely works.",
]

# -- aural / Intermediate: cadences, error detection, longer dictation -----
MESSAGES[("aural", "Intermediate", "correct_streak")] = [
    "{streak} in a row. Authentic versus half cadence is becoming a feeling of arrival versus a comma.",
    "Streak of {streak}. You are catching the wrong note in a phrase like a proofreader catches typos.",
    "{streak} straight. Deceptive cadences are supposed to fool you, and they have stopped.",
    "A run of {streak}. Your dictation memory is holding full phrases now, not fragments.",
    "{streak} correct. The plagal cadence's soft landing reads clearly to you.",
    "Clean {streak}. You hear when the performance differs from the page, which is a conductor's skill.",
    "{streak} in a row. Phrase endings are telling you their function on the first listen.",
    "{streak} deep. Error detection this consistent means your inner template is solid.",
]
MESSAGES[("aural", "Intermediate", "lesson_complete")] = [
    "{skill} complete. A cadence is harmony's punctuation, and you are reading periods and commas by ear.",
    "Lesson done. Finding the altered note in a melody means you carried the original in your head. You did.",
    "{skill} finished. V to I lands like a door closing, and you heard the latch every time.",
    "That wraps {skill}. The deceptive move to vi works because of expectation, and yours is now educated.",
    "Set done. Longer dictation lines reward chunking by scale degree, and your chunks are growing.",
    "{skill} done. Comparing what you heard to what was written is real rehearsal skill, practiced ten times over.",
    "Lesson complete. Half cadences leave the sentence hanging, and you felt the hang, not just labeled it.",
    "{skill} wrapped. Cadence hearing turns form from a diagram into something you experience.",
]
MESSAGES[("aural", "Intermediate", "level_up")] = [
    "{level} by ear. Cadences are sorted; full harmonic dictation is the next ascent.",
    "Aural reaches {level}. You hear phrases end. Next you transcribe everything inside them.",
    "New level: {level}. Your error detection says your inner ear is now a reliable reference.",
    "{level} now. Multi-voice listening is coming, and your single-line skills are ready to split attention.",
    "Welcome to {level}. From here the ear work resembles what conductors and producers actually do.",
    "Level up: {level}. Progressions next: hearing not just chords, but the story they tell in order.",
    "{level} reached. The dictations ahead carry full harmony. You have the cadence anchors to parse them.",
    "Aural hits {level}. Most ears plateau before this point. Yours did not.",
]
MESSAGES[("aural", "Intermediate", "comeback_after_miss")] = [
    "Good fix. You listened for the bass motion, falling fifth into the tonic, and the cadence confessed.",
    "Recovered. The deceptive cadence got you once, which is its job. You adjusted, which is yours.",
    "Back on it. The error was rhythmic, not melodic, and your second pass checked both layers.",
    "Right answer. A half cadence ends on V, not just near it, and your retry nailed the distinction.",
    "Corrected. You tracked scale degrees instead of raw pitches, and the line stopped slipping.",
    "There is the recovery. Long phrases need a second listen for the middle, and you spent it there.",
    "Nice catch on the retry. Plagal motion has no leading tone, and your ear went looking for one.",
    "Good adjustment. You compared the cadence to the phrase before it, and context settled the call.",
]
MESSAGES[("aural", "Intermediate", "mastery")] = [
    "{skill} mastered. Cadence hearing is form hearing, and form just became audible to you.",
    "Mastery: {skill}. You catch performance errors by ear, a skill ensembles pay real money for.",
    "{skill}: mastered. Full phrases go in your ear and come out on paper. That is dictation, done.",
    "Mastered: {skill}. Harmonic punctuation is now something you feel before you name.",
    "That locks {skill}. Your inner ear holds a reference copy and checks reality against it.",
    "{skill} settled. The multi-voice work ahead will lean on exactly this phrase memory.",
    "Mastery on {skill}. Expectation and arrival, the engine of tonal music, is audible to you now.",
    "{skill} is yours. Ten thousand musicians wish their ears did this reliably. Yours does.",
]
MESSAGES[("aural", "Intermediate", "daily_goal")] = [
    "Daily goal met. Phrase-length memory is built by daily listening, never by marathon sessions.",
    "Goal done. Cadence instincts stay calibrated through routine hearings, and today counted.",
    "Today's ear work is in. Detection skills dull fast without use; yours got used.",
    "Goal complete. Dictation stamina grows one daily session at a time, and one was added.",
    "That is today's goal. Your ear practiced judgment, not just exposure, which is the difference.",
    "Daily goal in. Intermediate ear training is a grind, and you are grinding it correctly.",
    "Done for today. Each session quietly lengthens the music you can hold in your head.",
    "Goal hit. The streak has carried you into legitimately hard listening, on schedule.",
]

# -- aural / Advanced: harmonic dictation, multi-part dictation ------------
MESSAGES[("aural", "Advanced", "correct_streak")] = [
    "{streak} in a row on harmonic dictation. You hear progressions as sentences, bass line first.",
    "Streak of {streak}. Two voices at once and your attention is splitting cleanly between them.",
    "{streak} straight. Roman numerals from sound alone, and the sound is cooperating.",
    "A run of {streak}. The inner voices are no longer hiding from you.",
    "{streak} correct. You track soprano and bass as a frame and infer the middle. Textbook technique.",
    "Clean {streak}. Full textures used to wash over you; now they arrive sorted.",
    "{streak} in a row. Predominant, dominant, tonic: you hear function arriving before the chord finishes.",
    "{streak} without a miss in multi-voice work. That is recital-committee territory.",
]
MESSAGES[("aural", "Advanced", "lesson_complete")] = [
    "{skill} complete. Harmonic dictation is hearing the bass and trusting it, and your trust is earned now.",
    "Lesson done. Three voices at once, and you kept each thread separate. The texture is opening up.",
    "{skill} finished. Hearing a progression and writing its numerals is analysis at the speed of sound.",
    "That wraps {skill}. The bass line carries the harmony's skeleton, and you transcribed the bones.",
    "Set done. Suspensions resolve down by step, and you heard each one lean and settle.",
    "{skill} done. Four-part hearing is the summit of dictation, and you climbed another stretch of it.",
    "Lesson complete. You held one voice steady in memory while writing another. That is the hard skill.",
    "{skill} wrapped. What a conductor hears in rehearsal, you just practiced deliberately.",
]
MESSAGES[("aural", "Advanced", "level_up")] = [
    "{level} by ear. Full-texture hearing is no longer aspirational for you. It is documented.",
    "Aural reaches {level}. You transcribe harmony from sound, which puts your ear among the trained few.",
    "New level: {level}. Multi-part dictation cleared. Whatever you listen to now arrives in layers.",
    "{level} now. Your ear does what theory class only describes.",
    "Welcome to {level}. Dictation at this band is the skill that separates listeners from hearers.",
    "Level up: {level}. Your ear now hands you the bass line and the function above it on demand.",
    "{level} reached. Few ears get formal training this far. Yours just tested into it.",
    "Aural hits {level}. From here, refinement comes from real repertoire, and you are equipped to hear it.",
]
MESSAGES[("aural", "Advanced", "comeback_after_miss")] = [
    "Good fix. You went back to the bass line, and the progression rebuilt itself from the bottom.",
    "Recovered. One voice slipped out of memory mid-phrase; the second listen budgeted attention better.",
    "Back on it. The chord was an inversion, not a new harmony, and your retry checked the bass first.",
    "Right answer. Six-four chords decorate the dominant more often than not, and you remembered.",
    "Corrected. You separated the voices by register on the retry, and the middle line stopped vanishing.",
    "There is the recovery. The miss was the soprano's leap, not the harmony, and you isolated it.",
    "Nice adjustment. Even trained ears lose a voice; the skill is noticing which one, and you did.",
    "Good correction. The progression made sense once you trusted the cadence and worked backward.",
]
MESSAGES[("aural", "Advanced", "mastery")] = [
    "{skill} mastered. Harmonic hearing at this level is permanent equipment. It travels everywhere with you.",
    "Mastery: {skill}. You hear in score order now, voices stacked and separate.",
    "{skill}: mastered. Dictation this deep means you can study music away from any instrument.",
    "Mastered: {skill}. The texture has no more hiding places.",
    "That locks {skill}. Conductors and producers use exactly this hearing daily. Now it is yours too.",
    "{skill} settled. Whole progressions transfer from air to paper through your ear, verified.",
    "Mastery on {skill}. Multi-voice transcription is a rare credential, and you earned it one phrase at a time.",
    "{skill} is yours. Music now arrives at your ear pre-analyzed.",
]
MESSAGES[("aural", "Advanced", "daily_goal")] = [
    "Daily goal met. Advanced ears need daily calibration the way instruments need tuning, and you tuned.",
    "Goal done. Multi-voice attention is perishable; today's session preserved it.",
    "Today's ear work is in. At this level, maintaining is achieving.",
    "Goal complete. You did surgeon-grade listening today and logged it like a habit. Correct approach.",
    "That is the day's goal. Harmonic dictation stamina is built exactly this unglamorously.",
    "Daily goal in. The streak now includes some of the hardest listening a musician can practice.",
    "Done for today. Your future self at a rehearsal will quietly thank this session.",
    "Goal hit. Daily contact with dense textures is what keeps them transparent.",
]

# -- aural / Graduate: atonal hearing, dense textures, fine discrimination -
MESSAGES[("aural", "Graduate", "correct_streak")] = [
    "{streak} in a row at the graduate tier. You are hearing structures most listeners do not know exist.",
    "Streak of {streak}. Atonal intervals, no key to lean on, and your ear is naming them anyway.",
    "{streak} straight. Four-voice textures are arriving at your ear already sorted into parts.",
    "A run of {streak}. You hear sonorities as set classes now, quality without tonality.",
    "{streak} correct. Chromatic lines with no tonal anchors, and your hearing held its line.",
    "Clean {streak}. The discrimination you are showing is what committees mean by trained ears.",
    "{streak} in a row. Your ear keeps its precision even when the music abandons every familiar landmark.",
    "{streak} deep into the hardest listening in the curriculum. The instrument between your ears is built.",
]
MESSAGES[("aural", "Graduate", "lesson_complete")] = [
    "{skill} complete. Hearing without a tonal center is its own skill, and you just practiced it deliberately.",
    "Lesson done. Dense chromatic dictation rewards interval-by-interval honesty, and you stayed honest.",
    "{skill} finished. You held a full texture in memory and reproduced it. Past this there is only repertoire.",
    "That wraps {skill}. The trichords are getting fingerprints, the way triads did years of skill ago.",
    "Set done. Listening at this density is concentration training as much as ear training, and you did both.",
    "{skill} done. Your ear handled material written to defeat habitual hearing.",
    "Lesson complete. What you just transcribed would silence most conservatory seniors.",
    "{skill} wrapped. At this tier every correct answer is a small research finding about your own ear.",
]
MESSAGES[("aural", "Graduate", "level_up")] = [
    "{level} by ear. There is no syllabus past this. There is only music, and you can hear all of it.",
    "Aural reaches {level}. Your hearing is now a research instrument.",
    "{level} confirmed. You hear tonal, post-tonal, and everything between with the same precision.",
    "Welcome to {level}. The ear-training pyramid has a top, and you are standing on it.",
    "New level: {level}. From single intervals years ago to full atonal textures now. The whole arc, walked.",
    "Level up: {level}. Hearing at this band is a working credential in any rehearsal room on earth.",
    "{level} reached. Trained hearing this complete changes what music even is for you.",
    "Aural hits {level}. Whatever the score does next, your ear arrives already prepared.",
]
MESSAGES[("aural", "Graduate", "comeback_after_miss")] = [
    "Good fix. With no key to orient you, you rebuilt from the lowest voice, which is the right scaffold.",
    "Recovered. Interval class 6 inverts to itself; the tritone played its usual trick, once.",
    "Back on it. Dense textures punish divided attention, and your retry committed to one voice at a time.",
    "Right answer. You checked the contour before the exact pitches, coarse before fine. Proper order.",
    "Corrected. Even at this level the ear anchors to the loudest voice; you consciously moved the anchor.",
    "There is the recovery. The set was inverted, not transposed, and your second hearing caught the mirror.",
    "Nice adjustment. Graduate ears still miss; they just diagnose the miss precisely, as you did.",
    "Good correction. You slowed your internal replay down, and the cluster resolved into pitches.",
]
MESSAGES[("aural", "Graduate", "mastery")] = [
    "{skill} mastered. Your ear now operates past the edge of standard training. That is rare air.",
    "Mastery: {skill}. Atonal hearing, verified and durable. Few musicians ever document this.",
    "{skill}: mastered. The most resistant material in aural training just yielded.",
    "Mastered: {skill}. Hearing this refined took years of layered skills, every one of them yours.",
    "That locks {skill}. Your inner ear plays back complex textures with the fidelity of a recording.",
    "{skill} settled. From here your ear improves only by meeting harder music, and very little qualifies.",
    "Mastery on {skill}. This is editor-grade listening, fully installed.",
    "{skill} is yours. The curriculum has nothing harder to offer your ears.",
]
MESSAGES[("aural", "Graduate", "daily_goal")] = [
    "Daily goal met. Elite hearing is maintained, never finished, and today was maintenance done right.",
    "Goal done. You practiced listening that has no shortcut, on a schedule that needs no willpower.",
    "Today's goal is in. The most refined skills decay first; yours got its daily defense.",
    "Goal complete. Graduate ears on a daily streak: the habit is as rare as the skill.",
    "That is the day. Precision listening, logged like a workout, which is exactly what it is.",
    "Daily goal in. You gave the hardest material the most reliable thing you have: routine.",
    "Done for today. The streak protects an ear that took years to build.",
    "Goal hit. Daily contact is why your hearing will still be sharp in a decade.",
]

# ===========================================================================
# piano
# ===========================================================================

# -- piano / Beginner: keyboard geography, finding notes -------------------
MESSAGES[("piano", "Beginner", "correct_streak")] = [
    "{streak} in a row. The two and three black-key groups are your landmarks now, and you are using them.",
    "Streak of {streak}. C sits left of the two black keys, and your hand goes there without negotiating.",
    "{streak} straight. You found each note from the key groups, not by counting up from middle C.",
    "A run of {streak}. The keyboard repeats every octave, and you are starting to trust the repetition.",
    "{streak} correct. Your eyes are on the staff more and the keys less. That is the trade you want.",
    "Clean {streak}. F lives left of the three black keys, and your fingers clearly got the memo.",
    "{streak} in a row at the keys. Geography first, music second, and your geography is filling in.",
    "{streak} without a miss. Each white key has a name, and your hands are learning to spell.",
]
MESSAGES[("piano", "Beginner", "lesson_complete")] = [
    "{skill} complete. Everything you ever play starts with knowing where the notes live, and you are learning the addresses.",
    "Lesson done. Learn one octave and you have learned them all; the pattern just repeats.",
    "{skill} finished. The black keys are not obstacles; they are the signposts, and you read them today.",
    "That wraps {skill}. Finding notes fast is what frees your eyes to read ahead in the score.",
    "Set done. Middle C is home base, and your hand found its way back from every direction.",
    "{skill} done. Keyboard geography is the piano's alphabet, and you traced more letters today.",
    "Lesson complete. Your reach for D no longer pauses to think. That pause was the enemy.",
    "{skill} wrapped. Hands that know the territory can start learning the music.",
]
MESSAGES[("piano", "Beginner", "level_up")] = [
    "{level} at the keys. You can find the notes; now you start connecting them into intervals and scales.",
    "Piano reaches {level}. The map is drawn. Next your fingers learn the routes between the landmarks.",
    "New level: {level}. Geography is done. Five-finger patterns and scale shapes come next.",
    "{level} now. Your hands pass the find-it test, so the curriculum starts asking them to travel.",
    "Welcome to {level}. From single keys to distances between keys: the playing gets musical from here.",
    "Level up: {level}. The keyboard stopped being a wall of identical keys somewhere back there.",
    "{level} reached. Notes on demand, both hands, anywhere on the keyboard. That was the entry exam.",
    "Piano hits {level}. The instrument is familiar now. Time to make it do things.",
]
MESSAGES[("piano", "Beginner", "comeback_after_miss")] = [
    "Good fix. You checked the black-key group before committing, and the right key was waiting.",
    "Recovered. E and F sit side by side with no black key between; now your hand knows it too.",
    "Back on it. One octave too high is the classic beginner miss, and you corrected the register cleanly.",
    "Right key this time. You navigated from the nearest landmark instead of guessing. Keep that habit.",
    "Corrected. B and C touch; the gap your hand expected is not there, and now it expects correctly.",
    "There it is. Looking down once to recalibrate is fine. The goal is needing it less each week.",
    "Nice recovery. Sharps sit up and to the right, and your hand found the right neighbor.",
    "Good adjustment. Wrong key, quick fix, no spiral. That is healthy practice behavior.",
]
MESSAGES[("piano", "Beginner", "mastery")] = [
    "{skill} mastered. Your hands know the keyboard the way your feet know your own stairs.",
    "Mastery: {skill}. Note-finding is now a background process, which frees the foreground for music.",
    "{skill}: mastered. The keyboard's geography is permanent knowledge now, like a hometown.",
    "Mastered: {skill}. Every future scale and chord shape gets built on this floor plan.",
    "That locks {skill}. No more searching; your hands arrive at notes like they were sent for.",
    "{skill} settled. Eyes on the score, hands on autopilot. That is the pianist's division of labor.",
    "Mastery on {skill}. The instrument is mapped. What happens on it next is up to you.",
    "{skill} is yours. Eighty-eight keys, zero strangers.",
]
MESSAGES[("piano", "Beginner", "daily_goal")] = [
    "Daily goal met. Hands learn through daily touch; today their lesson got delivered.",
    "Goal done. Keyboard familiarity is built in minutes a day, never in marathons.",
    "Today's keys are in. Motor memory consolidates overnight, so tonight does half the work.",
    "Goal reached. Your hands showed up today, and hands keep honest records.",
    "That is the day's goal. Little and often is the oldest piano advice there is, and it is still right.",
    "Daily goal complete. Each session shaves a little hesitation off your reach.",
    "Done for today. The keyboard rewards the player who visits daily, and you visit daily.",
    "Goal hit. Consistency at the keys this early sets the pattern for everything after.",
]

# -- piano / Early: play intervals, play scales, five-finger patterns ------
MESSAGES[("piano", "Early", "correct_streak")] = [
    "{streak} in a row. A fifth is a hand shape to you now, thumb and pinky, no measuring.",
    "Streak of {streak}. Scale fingering is starting to run itself, thumb tucking on schedule.",
    "{streak} straight. Your hands are playing distances, not hunting individual keys.",
    "A run of {streak}. Thirds fall under alternating fingers, and yours alternate without instruction.",
    "{streak} correct. The whole and half steps of the major scale are living in your fingers now.",
    "Clean {streak}. You are placing intervals by feel, with your eyes a beat ahead.",
    "{streak} in a row. The five-finger position is home, and you are venturing out and returning cleanly.",
    "{streak} at the keys without a miss. Spatial memory is the quiet skill, and yours is compounding.",
]
MESSAGES[("piano", "Early", "lesson_complete")] = [
    "{skill} complete. An interval at the keyboard is a distance your hand can memorize, and it is memorizing.",
    "Lesson done. The thumb crossing is the whole trick of scale playing, and you drilled it where it counts.",
    "{skill} finished. Octaves stretch the hand and calibrate it at the same time. Today did both.",
    "That wraps {skill}. Scales are not exercises in disguise; they are the actual material of pieces.",
    "Set done. Every interval you placed today is a chord you will place tomorrow.",
    "{skill} done. The black-key scales teach the hand more than the white ones, and you took the better lesson.",
    "Lesson complete. Playing a sixth without looking is a small physical fact you now own.",
    "{skill} wrapped. Finger numbers are turning into reflexes, which is exactly their retirement plan.",
]
MESSAGES[("piano", "Early", "level_up")] = [
    "{level} at the piano. Intervals and scales are under your fingers; chords are next, three notes at once.",
    "Piano reaches {level}. Your hands moved from finding to traveling. Now they learn to stack.",
    "New level: {level}. Scale shapes settled in, so the curriculum starts handing you harmonies.",
    "{level} now. Triads at the keyboard are intervals played together, and your intervals are ready.",
    "Welcome to {level}. The single-line phase is ending. Both hands have bigger plans.",
    "Level up: {level}. Your scale fingering survived scrutiny, which is more than most self-taught players can say.",
    "{level} reached. The hand shapes you drilled are about to become chord voicings.",
    "Piano hits {level}. From melodic distance to harmonic depth. The instrument gets fuller from here.",
]
MESSAGES[("piano", "Early", "comeback_after_miss")] = [
    "Good fix. You re-measured the interval from the lower note, and the hand landed true.",
    "Recovered. The thumb crossed one note late, and your second pass put it back on schedule.",
    "Back on it. Fourths and fifths feel similar under the hand; your retry checked the stretch.",
    "Right notes this time. Slowing down to accuracy speed is the fix, and you found that speed.",
    "Corrected. The scale needed its sharp and your hand remembered on the second ascent.",
    "There it is. A missed interval is a calibration update, and your hand just installed it.",
    "Nice recovery. You reset your hand position before retrying instead of lunging. Textbook.",
    "Good adjustment. The miss was fingering, not knowledge, and you fixed it at the source.",
]
MESSAGES[("piano", "Early", "mastery")] = [
    "{skill} mastered. Intervals are hand shapes now, permanently filed in muscle.",
    "Mastery: {skill}. Your scales run clean, which means your fingers know the key signatures too.",
    "{skill}: mastered. Distance at the keyboard is solved; your hands measure without your eyes.",
    "Mastered: {skill}. The thumb crossing is automatic, and automatic is the highest grade fingering gets.",
    "That locks {skill}. Chord playing ahead will sit on these exact hand spans.",
    "{skill} settled. What the page calls an interval, your hand now calls a position.",
    "Mastery on {skill}. Scale fluency at the keys quietly upgrades everything else you play.",
    "{skill} is yours. The patterns drilled here will show up in every piece you ever read.",
]
MESSAGES[("piano", "Early", "daily_goal")] = [
    "Daily goal met. Hands consolidate technique overnight; today's session gave them material.",
    "Goal done. Scales respond to daily visits faster than any other practice investment.",
    "Today's keyboard work is in. Short daily reps beat long rare ones, especially for fingers.",
    "Goal reached. The five-finger patterns got their daily maintenance, and they hold their value.",
    "That is today's goal. Technique is a garden; you watered it.",
    "Daily goal complete. Your hands now expect to practice daily, which is half the battle won.",
    "Done for today. Interval shapes fade without touch, and you touched them.",
    "Goal hit. A daily streak at the keys is the most reliable teacher you will ever hire.",
]

# -- piano / Intermediate: chords and inversions under the hands -----------
MESSAGES[("piano", "Intermediate", "correct_streak")] = [
    "{streak} in a row. Triads are landing as single hand shapes, three fingers arriving together.",
    "Streak of {streak}. Major to minor is one finger sliding a half step, and your hand does it without ceremony.",
    "{streak} straight. You are grabbing chords, not assembling them note by note.",
    "A run of {streak}. Inversions are rotations of the same grip, and your hand is rotating cleanly.",
    "{streak} correct. Root position and both flips: your hand knows all three doors into a triad.",
    "Clean {streak}. Diminished triads need a tighter hand, and yours tightens on cue.",
    "{streak} chords without a miss. The keyboard is becoming a place where harmony is physical.",
    "{streak} in a row. Your hand reads chord symbols the way your eyes read words now.",
]
MESSAGES[("piano", "Intermediate", "lesson_complete")] = [
    "{skill} complete. A triad under the hand is theory you can feel, and you felt plenty today.",
    "Lesson done. First inversion puts the third on the bottom, and your hand now knows that as a shape.",
    "{skill} finished. Chord playing is the piano's whole social life: accompaniment starts here.",
    "That wraps {skill}. Augmented triads stretch evenly, and your hand learned the symmetry by touch.",
    "Set done. Each quality has its own grip, and your hands sorted the grips today.",
    "{skill} done. Block chords today, arpeggios and voicings tomorrow. The order is right.",
    "Lesson complete. You moved between chords without re-finding each note. That is the actual skill.",
    "{skill} wrapped. Harmony is now something your hands produce on request, not just something you label.",
]
MESSAGES[("piano", "Intermediate", "level_up")] = [
    "{level} at the piano. Chords are in hand, literally. Arpeggios and fuller textures are next.",
    "Piano reaches {level}. Your hands deliver harmony on demand now, which changes what you can play.",
    "New level: {level}. Triads cleared in all inversions. The repertoire doors start opening.",
    "{level} now. You play what the Roman numerals mean, which is where theory becomes music.",
    "Welcome to {level}. Accompanying a melody is within reach. That is a useful musician's milestone.",
    "Level up: {level}. The chord grips are reliable, so speed and voicing become the new work.",
    "{level} reached. Three-note shapes behaved; four-note sevenths are waiting for those hands.",
    "Piano hits {level}. From here, practice starts sounding like repertoire instead of exercises.",
]
MESSAGES[("piano", "Intermediate", "comeback_after_miss")] = [
    "Good fix. You checked which chord member belonged in the bass, and the inversion sorted itself.",
    "Recovered. The third is the quality carrier; your retry adjusted exactly that finger.",
    "Back on it. A diminished fifth feels narrower than the hand expects, and now yours expects it.",
    "Right chord this time. You built it from the root up instead of grabbing and hoping.",
    "Corrected. The inversion was right, the octave was off, and you spotted which problem was which.",
    "There it is. One wrong chord tone, found and fixed, beats ten lucky grabs.",
    "Nice recovery. You released the whole hand and reset the shape. That is how chords get repaired.",
    "Good adjustment. The flat key asked for a different geography, and your hand re-read the map.",
]
MESSAGES[("piano", "Intermediate", "mastery")] = [
    "{skill} mastered. Chord shapes live in your hands now, retrievable without thought.",
    "Mastery: {skill}. You can voice a triad any way a score asks, which is real keyboard harmony.",
    "{skill}: mastered. The grips are automatic; attention is free to listen instead of aim.",
    "Mastered: {skill}. Inversions are no longer variants to you. They are equals, as they should be.",
    "That locks {skill}. Lead sheets and figured bass both just became playable documents.",
    "{skill} settled. Harmony moved from your eyes to your hands, permanently.",
    "Mastery on {skill}. Every accompaniment pattern there is gets built from what you just secured.",
    "{skill} is yours. Three notes, one gesture, any quality, any inversion.",
]
MESSAGES[("piano", "Intermediate", "daily_goal")] = [
    "Daily goal met. Chord grips stay reliable through daily contact, and contact was made.",
    "Goal done. Harmonic hand shapes consolidate in sleep; you just queued tonight's batch.",
    "Today's chord work is in. The difference between knowing and owning is daily reps like these.",
    "Goal reached. Your hands practiced harmony today, which is the fastest route to fluent playing.",
    "That is the day's goal. Intermediate piano is where habits set, and yours are setting well.",
    "Daily goal complete. Each session moves another chord from constructed to grabbed.",
    "Done for today. The streak is teaching your hands that harmony is routine.",
    "Goal hit. Daily chords now, effortless accompaniment later. The exchange rate is favorable.",
]

# -- piano / Advanced: sevenths, arpeggios, voicing, sight-playing ---------
MESSAGES[("piano", "Advanced", "correct_streak")] = [
    "{streak} in a row. Seventh chords are landing as single gestures, four notes with one intention.",
    "Streak of {streak}. Your arpeggios are connecting registers without a seam at the thumb.",
    "{streak} straight. You are voicing chords, choosing what sings on top, not just sounding them.",
    "A run of {streak}. Progressions flow hand to hand now, ii to V to I without a layover.",
    "{streak} correct. Sight-playing this clean means your hands trust your eyes a full beat ahead.",
    "Clean {streak}. The keyboard work is starting to sound like music even when it is a drill.",
    "{streak} in a row. Voice leading at the keys, common tones held while the moving lines move. Real playing.",
    "{streak} without a miss at this level. The technique is becoming invisible, which is its job.",
]
MESSAGES[("piano", "Advanced", "lesson_complete")] = [
    "{skill} complete. Smooth voice leading between chords is the difference between playing and typing.",
    "Lesson done. Arpeggios are chords given a time dimension, and yours kept their shape at speed.",
    "{skill} finished. Keeping common tones while moving the rest: that is keyboard craft, drilled properly.",
    "That wraps {skill}. Four-note chords with a singing top note. That is what listeners actually hear.",
    "Set done. Reading and playing simultaneously is the pianist's core multitask, and you trained it.",
    "{skill} done. The progression work today is the engine room of every accompaniment job.",
    "Lesson complete. Your hands resolved sevenths down by step without being told. Theory has reached the fingers.",
    "{skill} wrapped. At this level, practice is rehearsal for music that does not exist yet.",
]
MESSAGES[("piano", "Advanced", "level_up")] = [
    "{level} at the piano. The playing is fluent; what remains is repertoire and mileage.",
    "Piano reaches {level}. Your hands execute what your theory knows, which is the whole goal of keyboard skills.",
    "New level: {level}. Sevenths and full progressions cleared. The instrument answers to you now.",
    "{level} now. You sight-play what intermediate players woodshed.",
    "Welcome to {level}. The keyboard skills here are the ones professional gigs quietly assume.",
    "Level up: {level}. Your hands have opinions about voicing now. That is an advanced symptom.",
    "{level} reached. The mechanical questions are settled; the musical ones are all that remain.",
    "Piano hits {level}. Score to sound with almost nothing lost in transit.",
]
MESSAGES[("piano", "Advanced", "comeback_after_miss")] = [
    "Good fix. The arpeggio broke at the thumb crossing, and you rebuilt just that joint.",
    "Recovered. You re-voiced the chord so the line on top could speak. That was the actual problem.",
    "Back on it. The seventh wanted to resolve down and your hand finally let it.",
    "Right this time. You isolated the one transition that failed instead of replaying the whole passage.",
    "Corrected. The misread was rhythm, not pitch, and your retry counted before it played.",
    "There it is. Advanced misses are usually planning errors; your hands needed a half second of lead time.",
    "Nice recovery. You dropped the tempo until clean, the oldest and best repair on the instrument.",
    "Good adjustment. The progression smoothed out the moment you stopped re-striking common tones.",
]
MESSAGES[("piano", "Advanced", "mastery")] = [
    "{skill} mastered. Your hands deliver finished musical sentences now, not just correct notes.",
    "Mastery: {skill}. It is now filed under things your hands simply do.",
    "{skill}: mastered. Keyboard harmony at this level is a professional credential in everything but paper.",
    "Mastered: {skill}. The gap between what you understand and what you can play just closed.",
    "That locks {skill}. Sight-playing fluency makes the whole printed repertoire browsable.",
    "{skill} settled. Your technique stopped being the limiting factor.",
    "Mastery on {skill}. What conservatory juries check for, your hands now volunteer.",
    "{skill} is yours. The instrument has become an output device for your musical thought.",
]
MESSAGES[("piano", "Advanced", "daily_goal")] = [
    "Daily goal met. Advanced technique is rented, not owned; today's session paid the rent.",
    "Goal done. Hands at this level need daily motion the way athletes need training days.",
    "Today's keyboard work is in. Fluency is maintained in minutes a day and lost in weeks of none.",
    "Goal reached. You practiced like a professional today: on schedule, regardless of mood.",
    "That is the day's goal. The polish on advanced playing comes from exactly this regularity.",
    "Daily goal complete. The streak now guards skills that took years to build.",
    "Done for today. Daily touch keeps the difficult passages from re-becoming difficult.",
    "Goal hit. Repertoire-level hands, maintained the only way they can be.",
]

# -- piano / Graduate: realization, transposition, full-score reading ------
MESSAGES[("piano", "Graduate", "correct_streak")] = [
    "{streak} in a row. You are realizing harmony at the keys the way continuo players did for a living.",
    "Streak of {streak}. Transposition on the fly, and your hands are doing the interval math silently.",
    "{streak} straight. Open voicings across both hands, balanced and intentional, again and again.",
    "A run of {streak}. Score-reading reflexes this clean are what collaborative pianists get hired for.",
    "{streak} correct. Figured bass to full texture in real time. The eighteenth century would approve.",
    "Clean {streak}. Your hands improvise correct voice leading now, which means the rules became instinct.",
    "{streak} in a row at the instrument's deep end. Keyboard skills do not go higher than this.",
    "{streak} without a miss. At this tier, accuracy is artistry's load-bearing wall, and yours holds.",
]
MESSAGES[("piano", "Graduate", "lesson_complete")] = [
    "{skill} complete. Realizing figures at sight was the old conservatory's final exam, and you just took a page of it.",
    "Lesson done. Keyboard harmony at this level is composition at performance speed.",
    "{skill} finished. The page gave you numbers and your hands gave back four-part harmony, in time.",
    "That wraps {skill}. Transposing at sight means reading the music as intervals, and your hands agree.",
    "Set done. The textures you built today would pass a continuo audition.",
    "{skill} done. Graduate keyboard work is where theory, ear, and hands stop being separate subjects.",
    "Lesson complete. Every exercise here is a small act of composition, and you completed ten.",
    "{skill} wrapped. This is the keyboard fluency that lets scholars hear what they read.",
]
MESSAGES[("piano", "Graduate", "level_up")] = [
    "{level} at the piano. The curriculum's last door, and your hands opened it.",
    "Piano reaches {level}. Keyboard skills at this band are taught one-on-one in studios, and you drilled your way there.",
    "New level: {level}. You play harmony the way a fluent speaker talks, unrehearsed and correct.",
    "{level} now. Score to hands with no intermediate steps left to remove.",
    "Welcome to {level}. From finding middle C to realizing figured bass. That is the whole road, traveled.",
    "Level up: {level}. The instrument is transparent to your intentions now.",
    "{level} reached. Keyboard musicianship this complete is the rarest skill the app teaches.",
    "Piano hits {level}. Whatever you study from here, your hands can demonstrate it.",
]
MESSAGES[("piano", "Graduate", "comeback_after_miss")] = [
    "Good fix. The realization broke at the cadential six-four, and you re-voiced it by rule.",
    "Recovered. Transposition slipped a step at the accidental; your second pass tracked the new key signature.",
    "Back on it. You thinned the voicing until the voice leading was honest, then rebuilt. Proper craft.",
    "Right this time. Even continuo masters check the figures twice on a chromatic bass.",
    "Corrected. The error was doubling the leading tone, and you caught it before the resolution did.",
    "There is the repair. At this level misses are subtle, and so was your diagnosis.",
    "Nice recovery. You kept the bass and soprano frame and rebuilt the inner voices. Exactly right.",
    "Good adjustment. One flawed resolution, caught and reworked on the spot.",
]
MESSAGES[("piano", "Graduate", "mastery")] = [
    "{skill} mastered. This is the keyboard command that used to be every composer's day job.",
    "Mastery: {skill}. Your hands now hold the complete historical toolkit of the working keyboardist.",
    "{skill}: mastered. The keyboard is now a place where you think, not just a place where you play.",
    "Mastered: {skill}. Bach taught this skill to his students first. You arrived the long way, and you arrived.",
    "That locks {skill}. There is no higher keyboard credential in this curriculum to chase.",
    "{skill} settled. Your hands can demonstrate any harmony your mind can name.",
    "Mastery on {skill}. Teachers call this finished technique, and the term finally applies.",
    "{skill} is yours. Music passes from page to sound through you with nothing lost.",
]
MESSAGES[("piano", "Graduate", "daily_goal")] = [
    "Daily goal met. Mastery-level hands still need daily contact, and they got it.",
    "Goal done. The highest skills are the most perishable; today's session was preservation done right.",
    "Today's keyboard work is in. At the summit, routine is what keeps you there.",
    "Goal reached. You maintain graduate-level hands the same way you built them, one day at a time.",
    "That is the day's goal. Even finished technique gets a daily once-over, and yours got it.",
    "Daily goal complete. The streak now protects the rarest skills in your possession.",
    "Done for today. Continuo hands stay alive on daily contact, and contact was made.",
    "Goal hit. A daily habit at this level is what separates active mastery from a former skill.",
]
