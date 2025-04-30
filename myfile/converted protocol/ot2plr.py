# NF‑κB Luciferase Reporter Assay – pylabrobot version
# This script automates the luciferase activity measurement protocol using
# pylabrobot and the custom backend you created earlier today.

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends.opentrons_backend_jump import OpentronsBackend  # ← change to your backend class
from pylabrobot.resources import Coordinate, TipRack, Plate
from pylabrobot.resources.opentrons import (
corning_96_wellplate_360ul_flat,
    nest_12_reservoir_15ml,
    nest_1_reservoir_195ml,
    opentrons_96_tiprack_300ul
)

# ──────────────────────────────────────
# User‑configurable constants (µL)
MEDIUM_VOL = 100     # volume of spent medium to remove
PBS_VOL    = 50      # PBS wash volume
LYSIS_VOL  = 30      # lysis buffer volume
LUC_VOL    = 100     # luciferase reagent volume
TOTAL_COL  = 12      # process A1–A12

# ──────────────────────────────────────
def _build_deck(lh: LiquidHandler):
    """Load all labware on the deck and return handy shortcuts."""
    # Tip‑racks on slots 8, 11, 1, 4  (order preserved to match Opentrons layout)
    tiprack_slots = [8, 11, 1, 4]
    tiprack_i = opentrons_96_tiprack_300ul(
            name=tiprack)

    tiprack = [lh.deck.assign_child_resource(tiprack_i, slot=slot_i) for slot_i in tiprack_slots]
    # Working 96‑well plate at slot 6
    working_plate = corning_96_wellplate_360ul_flat(name="working_plate")
    lh.deck.assign_child_resource(working_plate, slot=6)

    # 12‑channel reservoir (PBS, Lysis, Luciferase) at slot 3
    reagent_stock = nest_12_reservoir_15ml(name=reagent_stock)
    lh.deck.assign_child_resource(reagent_stock, slot=3)

    # 1‑channel waste reservoir at slot 9
    waste_res = nest_1_reservoir_195ml(name=waste_res)
    lh.deck.assign_child_resource(waste_res, location=lh.deck.get_slot(9))

    return {
        "tip_racks"     : tiprack,
        "working_plate" : working_plate,
        "reagent_res"   : reagent_stock,
        "waste_res"     : waste_res
    }

# ──────────────────────────────────────
def _tip_gen(tip_racks):
    """Yield the next available tip."""
    for rack in tip_racks:
        for tip in rack:
            yield tip
    raise RuntimeError("Out of tips!")

# ──────────────────────────────────────
def run(simulation: bool = False):
    """Main entry point – set `simulation=True` to skip hardware calls."""
    backend = MyBackend(simulation=simulation)
    lh = LiquidHandler(backend=backend)
    deck = _build_deck(lh)
    tips = _tip_gen(deck["tip_racks"])

    # Handy aliases
    pbs        = deck["reagent_res"].wells()[0]
    lysis      = deck["reagent_res"].wells()[1]
    luciferase = deck["reagent_res"].wells()[2]
    waste      = deck["waste_res"].wells()[0]
    cells_all  = deck["working_plate"].rows()[0][:TOTAL_COL]  # A1–A12

    lh.setup()  # initialise backend (homing, etc.)

    # ────────── 1. Remove spent medium ──────────
    for cell in cells_all:
        lh.pick_up_tips(next(tips))
        lh.aspirate(cell, MEDIUM_VOL * 1.2, flow_rate=0.2,
                    offset=Coordinate(x=-2.5, y=0, z=0.2))
        lh.dispense(waste, MEDIUM_VOL * 1.2, flow_rate=3,
                    offset=Coordinate(z=-5))
        lh.drop_tips()

    # ────────── 2. PBS wash (add) ──────────
    lh.pick_up_tips(next(tips))
    for cell in cells_all:
        lh.aspirate(pbs, PBS_VOL, flow_rate=3)
        lh.air_gap(20)
        lh.dispense(cell, PBS_VOL + 20, flow_rate=0.3,
                    offset=Coordinate(z=-2))
    lh.drop_tips()

    # ────────── 3. PBS wash (remove) ──────────
    for cell in cells_all:
        lh.pick_up_tips(next(tips))
        lh.aspirate(cell, PBS_VOL * 1.5, flow_rate=0.2,
                    offset=Coordinate(x=-2.5, y=0, z=0.2))
        lh.dispense(waste, PBS_VOL * 1.5, flow_rate=3,
                    offset=Coordinate(z=-5))
        lh.drop_tips()

    # ────────── 4. Add lysis buffer ──────────
    lh.pick_up_tips(next(tips))
    for cell in cells_all:
        lh.aspirate(lysis, LYSIS_VOL, flow_rate=0.5)
        backend.delay(seconds=2)
        lh.dispense(cell, LYSIS_VOL, flow_rate=0.3,
                    offset=Coordinate(z=5))
        backend.delay(seconds=2)
    lh.drop_tips()
    backend.delay(minutes=3)

    # ────────── 5. Add luciferase reagent ──────────
    for cell in cells_all:
        lh.pick_up_tips(next(tips))
        lh.aspirate(luciferase, LUC_VOL, flow_rate=0.75)
        backend.delay(seconds=2)
        lh.dispense(cell, LUC_VOL, flow_rate=0.75,
                    offset=Coordinate(z=-0.5))
        lh.mix(cell, volume=75, repetitions=3, flow_rate=3,
               offset=Coordinate(z=0.5))
        lh.drop_tips()

    lh.finish()  # wrap‑up (home, log, etc.)

# ──────────────────────────────────────
if __name__ == "__main__":
    # Default to simulation mode so the script is safe to run on any machine.
    run(simulation=True)
