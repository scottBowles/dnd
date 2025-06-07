#!/usr/bin/env python
"""
Backwards-compatible transcription script.
This script maintains the same interface as the original transcription_script.py
but now uses the new Django app structure.
"""

import os
import sys
from pathlib import Path

# Add the Django project to the path
django_project_path = Path(__file__).parent
sys.path.append(str(django_project_path))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")

import django

django.setup()

from transcription.services import TranscriptionService

# Previous transcript for backwards compatibility
PREVIOUS_TRANSCRIPT = """
Hrotholf, Izar, Dorinda, and Ego awake in a plain, back in an ash pit, each with a blue light tether coming from their chest to the clew on Izar's ring.

Ego: How did we get here?! Did you all hear those gunshots?

Hrothulf: What? No. I believe my vile brother sent me to this place. Instead of facing me like a magman he sent myself and apparently all of y'all to this place.

Ego: How did he have the power to do that to all of us?

Hrothulf: He had me trapped in basically a giant cake glass thing and two Vradum knights appeared, and then the floor kind of gave way and… alacazam.

Ego: My head is burning up. You all don't hear the gunfire and artillery? I can't even think.

Dorinda tries to reassure Ego that none of that is happening hear. She encourages Ego to use the phoenix shell. Ego consumes the powder, and after it all goes down Ego has a gentle burp, and a light blue flame wafts over her body, top to bottom. When it completely flows over her body, she experiences healing. The sounds of gunpowder war are still there, but a little quieted. Her forehead still burns.

Dorinda turns to Izar and asks, "What is our objective here? I'm trying to see the point in what we're trying to do. I seem to have lost…" and she trails off.

Izar: "Why do you sound so sad? I thought her were a robot. Our mission is to get out of here. What do you think?"

Ego focuses on her forehead but also looks around to ensure her comrades are ok.

Hrothulf: "Are there bodies on the ground?"

Dorinda: No, there are no bodies, we see no bodies. Just an empty ash pit like we were in before.

Dorinda cries, "Servant, come and help us!"
She sits down, crosses her legs, and kind of assumes a neutral position.

Hrothulf goes over and starts feeling around on the ground.
"Uh yeah right over here. Y'all don't see these bodies?"

There are no bodies, Hrothulf.

Izar: But what if there are and he's the only one who can see them?

Hrothulf is touching the bodies he sees. They feel like dead bodies.
"I do recognize these people. They seem strangely familiar to me… behold it is my family!"

Ego:  "Is one of them Slenn?"
Izar: "They're all slain, I think."
Hrothulf: It's my beloved siblings, [Hrothgar, Wiglaf, Hildegar, and Brecca den Hrunting],  along with what appears to be a young salamander boy?
Ego: Do you think that this is how Slenn killed them?
Hrothulf: Indeed it may be.

Ego sees Dorinda has sat down, and Ego sits down too and focuses on her forehead.

Hrothulf is a little overcome in this moment. He knew they were gone but it's hard to see them like this.
Izar goes over and puts her hand on his should her.
Horthulf: "Y'all can't see this?"
Izar: "No."

Izar: Do the sounds you're hearing remind you of anything you've seen?
Ego: I know I heard it the last time I was in the ash pit. I'm not really sure otherwise.

Izar scoops ash off the ground and throws it, imagining Servant. It falls a little bit like dust in a light cloud. Izar hopes against hope to see a spark of flame or some image, but instead she just watches ash drift to the ground.

Hrohtulf sees Izar's thrown ash land on the forehead of Brecca.
All of us hear a booming voice that almost sounds like it's laughing but it just says one word: "BRANCH!"
The ashes on Brecca's forehead light up in a small fire. Orange fire bursts from the center here and leaps on Izar's ring, then sends a shockwave of flame that slowly erupts from the center where we are, and now we can all see the five bodies on the ground.

Dorinda stands up and says, "I think that was the answer to my prayer."
Izar: "You pray?!"
Dorinda: I mean, we're seeking these gods, right? So… I just. I don't know. Called on Gliten in my mind and said we were the Branch of Teresias and…"
Izar: Nice.

We notice the bodies are all laying on their backs, like they're sleeping. They're actually breathing. Oh and that salamander boy looks familiar too… it's the Prince.
Hrothulf: "Indeed upon further review they appear to be in full health but unresponsive. Although Hildegar has done something different with her hair that I don't recognize."
Hrothulf goes from person to person, making sure each is in the same condition. He gives a friendly jostle, but to no effect. They have no wounds or battle damage, but are in a very deep comatose kind of sleep.
Hrothulf gently waves the whiskey in his hip glass under Brecca's nose, but Brecca is still non-responsive. (Brecca was the king's vizier, an older mentor to Hrothulf.) 

We don't exactly recognize the voice, but it was jovial and powerful and it came right before the fire. It's somewhat reminiscent of the first time we heard a voice as we were escaping the temple of Thiten. This voice was more jovial and light-hearted, but it had the crackle of a thousand forest fires.
When the fire shot out it looked a little phoenix-y, but it was a low laying circle with the ring at the epicenter.

Responding to the voice, Izar: "Yes Gliton, it's us. Can you help us please?"

Ego: Izar, is there anything new in the bracelet?
Izar: There's nothing new except that the holy fire batman came out of it.

We position ourselves so that the beam goes through the bodies, through their hearts and/or through their heads, lying next to them and thinking hard about leaving this place.

The voice returns audibly, saying, "It appears as though we might have ourselves a little… game. The stakes: What would you give to bring these back?"
This voice is not ominous. It is equal parts frightening and welcoming. We're not afraid but we feel like we should be.

Dorinda can't seem to formulate an answer.
Ego has no control over her thoughts.
Izar: My… pinky finger?
Hrothulf: If it means bringing them back and destroying my brother, whatever it takes.

Gliton: Whatever it takes? I can work with that!

Izar: What do we have to give?
Gliton: Yes, good question. I know! I'll give you these people back, and if you find a way out of my land of repose, you bring me the head of Raltach. I have much use for that.
(Raltach is waiting for us in an arena in Champion City on Terran)

Izar: So… can you kind of be in a bunch of places at once? We'd have to get his head in Terran. Can we mail it, or… something with the ethereal realm I don't know?
You are the branch. You've found your way to my realm before we can find your way back. What do you say? You get what you want, I get what I want, and you go about your branchy way. 
Hrothulf: Once we have the aforementioned dragon cranium, how do we get back here?
I trust you'll figure that out, oh might branch.
Dorinda: Will you also assist us in our attempts to defeat Slenn and restore our friend to the rightful rule of his people if we do this.
Gliton: No I don't care about any of that.
But you do care about the skull of the dragon, right?
I care about the game! Oh, I and Raltach have some interesting history to attend to. Bad blood, you can probably find it in the book!
Izar: Yeah but you and the Vardum have bad blood too, right? Didn't they trap you here?
Gliton: No, I come here to rest.
Izar: Can we ask for an additional thing—a clue to Teresias, or Bode Augur—something about where he is or whatever.
Gliton: Information? Eh, you sound like my sister.
Izar: You can answer with action if you don't like information. Or some easier way for us to get Raltach's head to you?
Gliton: Given our current situation there are limitations. There are… ah… hows……. I don't know. There. I don't know where your Teresias is. I don't know where Bodie Augur is, but you could find Yafel and she could tell you. She's my nerdy sister.
Dorinda: And whence does she reside, my lord?
Gliton: "Ugh I wouldn't call what we're doing residing so much." He winces, catching himself for oversharing. I'm supposed to make this kind of a puzzle thing. I hate these things trivia games suck. "So… you'll find Yafel on the planet you know as Genussa. You'll find her deep in a chasm of unknowing, under a wise star. Ok can we do this or what? I've been alone for so long."
Izar: We can take you if you want!
Gliton: Can't we're kind of an all or nothing passage.
And an orange comet rockets toward us and it shrinks and lands in Izar's bracelet and burns itself into the bracelet.

The Heordred family and Ibi wake up, and our clew splits and connects to all nine of us. 

Hrothulf hugs his sister and gives Brecca the traditional Magman handshake that you would give to a peer.
"""


def main():
    """Main function that replicates the original script behavior."""
    try:
        print("🎙️  Starting D&D Audio Transcription Service")
        print("=" * 50)

        # Initialize the transcription service
        service = TranscriptionService()

        # Process all files with the previous transcript
        processed_count = service.process_all_files(
            session_number=1, previous_transcript=PREVIOUS_TRANSCRIPT
        )

        print("=" * 50)
        print(f"✅ Transcription complete! Processed {processed_count} files.")

    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
