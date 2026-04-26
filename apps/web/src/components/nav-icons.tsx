import {
  FiActivity,
  FiBookOpen,
  FiDroplet,
  FiHeart,
  FiHome,
  FiMonitor,
  FiPackage,
  FiScissors,
  FiShield,
  FiSmile,
  FiStar,
  FiSun,
  FiTruck
} from "react-icons/fi";
import { GiBrain, GiMedicines, GiMirrorMirror, GiStomach } from "react-icons/gi";
import { MdOutlineChildCare, MdOutlineRemoveRedEye } from "react-icons/md";
import { RiCapsuleLine } from "react-icons/ri";
import { TbBone, TbLungs, TbTemperature } from "react-icons/tb";
import type { IconType } from "react-icons";

const iconMap: Record<string, IconType> = {
  activity: FiActivity,
  baby: MdOutlineChildCare,
  bone: TbBone,
  brain: GiBrain,
  capsule: RiCapsuleLine,
  device: FiMonitor,
  drop: FiDroplet,
  eye: MdOutlineRemoveRedEye,
  flash: FiSun,
  guide: FiBookOpen,
  hair: FiScissors,
  heart: FiHeart,
  homeo: FiHome,
  leaf: GiMirrorMirror,
  lungs: TbLungs,
  medicine: GiMedicines,
  nosmoke: FiTruck,
  package: FiPackage,
  pills: FiPackage,
  shield: FiShield,
  smile: FiSmile,
  sparkles: FiStar,
  stomach: GiStomach,
  thermo: TbTemperature
};

export function getNavIcon(iconKey: string): IconType {
  return iconMap[iconKey] ?? FiStar;
}
