import { returnClass, returnLabel } from "../format";

export default function StampBadge({ value, beatMargin = 0.05 }: { value: number | null | undefined; beatMargin?: number }) {
  return <span className={`stamp-badge ${returnClass(value, beatMargin)}`}>{returnLabel(value, beatMargin)}</span>;
}
