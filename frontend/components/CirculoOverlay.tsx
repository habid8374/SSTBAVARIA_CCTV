type Props = {
  centro: [number, number];
  radioPx: number;
  naturalWidth: number;
  naturalHeight: number;
  color?: string;
  dashed?: boolean;
  fillOpacity?: number;
};

export default function CirculoOverlay({
  centro,
  radioPx,
  naturalWidth,
  naturalHeight,
  color = "#f59e0b",
  dashed = true,
  fillOpacity = 0.18,
}: Props) {
  if (!naturalWidth || !naturalHeight || radioPx <= 0) return null;

  const [cx, cy] = centro;
  const grosor = Math.max(naturalWidth * 0.004, 1.5);

  return (
    <svg
      viewBox={`0 0 ${naturalWidth} ${naturalHeight}`}
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <circle
        cx={cx}
        cy={cy}
        r={radioPx}
        fill={color}
        fillOpacity={fillOpacity}
        stroke={color}
        strokeWidth={grosor}
        strokeDasharray={dashed ? `${grosor * 3} ${grosor * 2}` : undefined}
      />
      <circle cx={cx} cy={cy} r={grosor * 2.2} fill={color} />
    </svg>
  );
}
