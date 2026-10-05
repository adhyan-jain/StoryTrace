"""Surface forms. Template pools are split into TRAIN and HELD-OUT lists; entity pools are disjoint across splits."""
from __future__ import annotations

CHARS_A = ["Alice", "Bob", "Charlie", "Diana", "Edgar", "Fiona", "Gareth", "Hana", "Ivan", "Jasmine",
           "Kofi", "Lena", "Marco", "Nadia", "Omar", "Priya"]
CHARS_B = ["Quentin", "Rosalind", "Soren", "Talia", "Ulrich", "Vera", "Wendell", "Xiomara", "Yusuf", "Zelda"]
CHARS_NEAR = ["Ann", "Anna", "Anne", "Marc", "Mark", "Marcus", "Jon", "John", "Joan"]
PROPS_A = ["brass key", "silver dagger", "ancient map", "leather satchel", "glass vial", "iron lantern",
           "wooden flute", "torn letter", "jade ring", "copper coin"]
PROPS_B = ["crystal compass", "velvet cloak", "bone whistle", "ivory comb", "tin trumpet", "amber locket"]
PROPS_NEAR = ["brass key", "brass keyring", "iron key", "iron keyring", "paper map", "paper mask"]
LOCS_A = ["library", "armory", "courtyard", "tower", "cellar", "kitchen", "chapel", "stable", "garden", "gatehouse"]
LOCS_B = ["observatory", "boathouse", "greenhouse", "orchard", "workshop", "dormitory"]
LOCS_NEAR = ["north tower", "south tower", "east tower", "north gate", "south gate"]

# (train, heldout)
EVENT_TPL = {
    "move": (["{a} walked to the {L}", "{a} headed over to the {L}", "{a} made their way to the {L}",
              "{a} went into the {L}", "{a} moved to the {L}"],
             ["{a} strolled across to the {L}", "{a} relocated to the {L}", "{a} set off for the {L} and arrived there"]),
    "give": (["{a} handed the {p} to {b}", "{a} gave {b} the {p}", "{a} passed the {p} over to {b}",
              "{a} entrusted {b} with the {p}", "{a} let {b} take the {p}"],
             ["{b} received the {p} from {a}", "{a} slipped the {p} into {b}'s hands", "{a} transferred the {p} to {b}"]),
    "pickup": (["{a} picked up the {p}", "{a} grabbed the {p}", "{a} took the {p} from the floor",
                "{a} lifted the {p}", "{a} collected the {p}"],
               ["{a} scooped up the {p}", "{a} pocketed the {p}", "{a} snatched up the {p}"]),
    "drop": (["{a} put down the {p}", "{a} dropped the {p}", "{a} set the {p} down", "{a} left the {p} on the floor",
              "{a} let go of the {p}"],
             ["{a} abandoned the {p}", "{a} laid the {p} aside", "{a} discarded the {p}"]),
    "injure": (["{a} was hurt", "{a} got injured", "{a} suffered a wound", "{a} was wounded", "{a} took a nasty fall"],
               ["{a} sprained an ankle", "{a} was cut badly", "{a} came away bruised and bleeding"]),
    "heal": (["{a} recovered", "{a} was healed", "{a} got better", "{a} felt well again", "{a} was patched up"],
             ["{a} made a full recovery", "{a} shook off the injury", "{a} was nursed back to health"]),
    "noop": (["{a} hummed a quiet tune", "{a} glanced at the ceiling", "{a} yawned", "{a} checked the time",
              "{a} admired the {p}", "{a} glanced at the {p}", "{a} talked about the {L}", "{a} muttered something"],
             ["{a} tapped a foot impatiently", "{a} stared out the window", "{a} cleared their throat",
              "{a} wondered about the {p}", "{a} chatted about the {L}"]),
}
ASSERT_TPL = {
    "loc": (["{a} was in the {L}", "{a} was seen in the {L}", "{a} was found in the {L}", "{a} was staying in the {L}"],
            ["{a} could be found in the {L}", "{a} stood in the {L}"]),
    "holder": (["{a} was carrying the {p}", "{a} had the {p}", "the {p} was with {a}"],
               ["{a} held the {p}", "the {p} was in {a}'s possession"]),
    "holder_nobody": (["nobody was holding the {p}", "the {p} was lying unattended"],
                      ["the {p} was lying about unclaimed", "no one had the {p}"]),
    "proploc": (["the {p} was in the {L}", "the {p} was located in the {L}"],
                ["the {p} could be found in the {L}", "the {p} was kept in the {L}"]),
    "injured": (["{a} was nursing an injury", "{a} was still wounded"], ["{a} was walking with a limp", "{a} was in pain"]),
    "unharmed": (["{a} was in good health", "{a} was unharmed"], ["{a} was perfectly fine", "{a} was free of injuries"]),
}
MARKERS = (["On day {t},", "Day {t}:", "During day {t},"], ["By the end of day {t},", "As day {t} unfolded,"])
INTRO_MARK = "At the start,"
INTRO_TPL = {
    "loc": "{a} was in the {L}.",
    "holder": "{a} was carrying the {p}.",
    "ground": "the {p} lay on the floor of the {L}.",
    "injured": "{a} was injured.",
}


def pool(table_entry, heldout: bool):
    return table_entry[1] if heldout else table_entry[0]
