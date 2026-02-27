#!/usr/bin/env python3

#
# school_factory.py
#
# Factory function to get character Schools for L7R combat simulator from the name of the school.
#

from simulation.schools.akodo_school import AkodoBushiSchool
from simulation.schools.bayushi_school import BayushiBushiSchool
from simulation.schools.courtier_school import CourtierSchool
from simulation.schools.daidoji_school import DaidojiYojimboSchool
from simulation.schools.doji_artisan_school import DojiArtisanSchool
from simulation.schools.hida_school import HidaBushiSchool
from simulation.schools.hiruma_school import HirumaScoutSchool
from simulation.schools.ikoma_bard_school import IkomaBardSchool
from simulation.schools.isawa_school import IsawaDuelistSchool
from simulation.schools.kakita_school import KakitaBushiSchool
from simulation.schools.kitsuki_school import KitsukiMagistrateSchool
from simulation.schools.kuni_school import KuniWitchHunterSchool
from simulation.schools.matsu_school import MatsuBushiSchool
from simulation.schools.merchant_school import MerchantSchool
from simulation.schools.mirumoto_school import MirumotoBushiSchool
from simulation.schools.monk_school import BrotherhoodOfShinseMonkSchool
from simulation.schools.otaku_school import OtakuBushiSchool
from simulation.schools.shiba_school import ShibaBushiSchool
from simulation.schools.shinjo_school import ShinjoBushiSchool
from simulation.schools.shosuro_actor_school import ShosuroActorSchool
from simulation.schools.yogo_school import YogoWardenSchool


def get_school(name):
    if not isinstance(name, str):
        raise ValueError("get_school name parameter must be str")
    if name == "Akodo Bushi School":
        return AkodoBushiSchool()
    elif name == "Bayushi Bushi School":
        return BayushiBushiSchool()
    elif name == "Brotherhood of Shinsei Monk School":
        return BrotherhoodOfShinseMonkSchool()
    elif name == "Courtier School":
        return CourtierSchool()
    elif name == "Daidoji Yojimbo School":
        return DaidojiYojimboSchool()
    elif name == "Doji Artisan School":
        return DojiArtisanSchool()
    elif name == "Hida Bushi School":
        return HidaBushiSchool()
    elif name == "Hiruma Scout School":
        return HirumaScoutSchool()
    elif name == "Ikoma Bard School":
        return IkomaBardSchool()
    elif name == "Isawa Duelist School":
        return IsawaDuelistSchool()
    elif name == "Kakita Bushi School":
        return KakitaBushiSchool()
    elif name == "Kitsuki Magistrate School":
        return KitsukiMagistrateSchool()
    elif name == "Kuni Witch Hunter School":
        return KuniWitchHunterSchool()
    elif name == "Matsu Bushi School":
        return MatsuBushiSchool()
    elif name == "Merchant School":
        return MerchantSchool()
    elif name == "Mirumoto Bushi School":
        return MirumotoBushiSchool()
    elif name == "Otaku Bushi School":
        return OtakuBushiSchool()
    elif name == "Shiba Bushi School":
        return ShibaBushiSchool()
    elif name == "Shinjo Bushi School":
        return ShinjoBushiSchool()
    elif name == "Shosuro Actor School":
        return ShosuroActorSchool()
    elif name == "Yogo Warden School":
        return YogoWardenSchool()
    else:
        raise ValueError(f"Unsupported school: {name}")
