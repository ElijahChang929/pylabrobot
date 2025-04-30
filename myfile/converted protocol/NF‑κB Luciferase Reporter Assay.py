# NF‑κB Luciferase Reporter Assay – pylabrobot version

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends.opentrons_backend_jump import OpentronsBackend  # ← change to your backend class
from pylabrobot.resources import Coordinate, TipRack, Plate
from pylabrobot.resources.opentrons import (
corning_96_wellplate_360ul_flat,
    nest_12_reservoir_15ml,
    nest_1_reservoir_195ml,
    opentrons_96_tiprack_300ul
)
from High_level_function.action_defination import DPLiquidHandler

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
async def run(simulation: bool = True):
    """Main entry point – set `simulation=True` to skip hardware calls."""
    backend = MyBackend(simulation=simulation)
    lh = DPLiquidHandler(backend=backend)
    deck = _build_deck(lh)

    # Handy aliases
    pbs        = deck["reagent_res"].wells()[0]
    lysis      = deck["reagent_res"].wells()[1]
    luciferase = deck["reagent_res"].wells()[2]
    cells_all  = deck["working_plate"].rows()[0][:TOTAL_COL]  # A1–A12

    lh.setup()  # initialise backend (homing, etc.)

    # ────────── 1. Remove spent medium ──────────
    await lh.remove_liquid(
        vols=[MEDIUM_VOL]*12,
        sources=cells_all,
        tip_racks=deck["tip_racks"],
        offsets=[Coordinate(x=-2.5, y=0, z=-0.2),Coordinate(x=0, y=0, z=-5)],
        liquid_height=[0.2,None],
        flow_rates=[0.2,3]
    )

    # ────────── 2. PBS wash (add) ──────────
    await lh.add_liquid(
        vols=[PBS_VOL]*12,
        reagent_sources=[pbs],
        targets=cells_all,
        delays=[1],
        tip_racks=deck["tip_racks"],
        flow_rates=[3,0.3],
        offsets=[Coordinate(x=0, y=0, z=0.5),Coordinate(x=0, y=0, z=-2)],
        blow_out_air_volume=[20,None]
    )

    # ────────── 3. PBS wash (remove) ──────────

    await lh.remove_liquid(
        vols=[PBS_VOL * 1.5]*12,
        liquid_height=[0.2,None],
        offsets=[Coordinate(x=-2.5, y=0, z=0),Coordinate(x=0, y=0, z=-5)],
        sources=cells_all,
        tip_racks=deck["tip_racks"]
    )

    # ────────── 4. Add lysis buffer ──────────

    await lh.add_liquid(
        vols=[LYSIS_VOL]*12,
        reagent_sources=[lysis],
        sources=cells_all,
        delays=[2,2],
        tip_racks=deck["tip_racks"]
    )

    # ────────── 5. Add luciferase reagent ──────────

    await lh.add_liquid(
        vols=[LUC_VOL]*12,
        reagent_sources=[luciferase],
        targets=cells_all,
        delays=[1],
        tip_racks=deck["tip_racks"],
        mix_time=[3],
        mix_vols=[75],
        mix_liquid_height=[0.5]
    )

# ──────────────────────────────────────
if __name__ == "__main__":
    # Default to simulation mode so the script is safe to run on any machine.
    run(simulation=True)
