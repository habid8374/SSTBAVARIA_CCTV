type Props = {
  puntos: number[][];
  naturalWidth: number;
  naturalHeight: number;
  color?: string;
  dashed?: boolean;
  fillOpacity?: number;
};

export default function PoligonoOverlay({
  puntos,
  naturalWidth,
  naturalHeight,
  color = "#f59e0b",
  dashed = true,
  fillOpacity = 0.18,
}: Props) {
  if (puntos.length < 2 || !naturalWidth || !naturalHeight) return null;

  const pointsAttr = puntos.map(([x, y]) => `${x},${y}`).join(" ");
  const grosor = Math.max(naturalWidth * 0.004, 1.5);

  return (
    <svg
      viewBox={`0 0 ${naturalWidth} ${naturalHeight}`}
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      {puntos.length >= 3 ? (
        <polygon
          points={pointsAttr}
          fill={color}
          fillOpacity={fillOpacity}
          stroke={color}
          strokeWidth={grosor}
          strokeDasharray={dashed ? `${grosor * 3} ${grosor * 2}` : undefined}
        />
      ) : (
        <polyline
          points={pointsAttr}
          fill="none"
          stroke={color}
          strokeWidth={grosor}
          strokeDasharray={dashed ? `${grosor * 3} ${grosor * 2}` : undefined}
        />
      )}
      {puntos.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={grosor * 2.2} fill={color} />
      ))}
    </svg>
  );
}
