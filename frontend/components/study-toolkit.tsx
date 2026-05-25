"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { evaluate } from "mathjs";
import {
  Calculator,
  Eraser,
  FunctionSquare,
  NotebookPen,
  Palette,
  Pencil,
  Redo2,
  Trash2,
  Undo2,
  X
} from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { calculateFinancialValue, type FinancialMode } from "@/lib/financial-calculator";
import { prepareFunctionPlot } from "@/lib/function-plot";

type ToolkitTab = "whiteboard" | "calculator" | "graph" | "notes";
type CalculatorMode = "basic" | "scientific" | "financial";

const colors = [
  { label: "black", value: "#111111" },
  { label: "blue", value: "#2563eb" },
  { label: "red", value: "#dc2626" },
  { label: "green", value: "#16a34a" },
  { label: "gold", value: "#f5c542" }
];
const markerSizes = [
  { label: "Small", value: 3 },
  { label: "Medium", value: 7 },
  { label: "Large", value: 14 }
];
const defaultNotesScope = "global";

export function openStudyToolkit(scope = defaultNotesScope): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent("open-study-toolkit", { detail: { scope } }));
}

export function StudyToolsButton({ scope, className }: { scope?: string; className?: string }) {
  return (
    <Button type="button" variant="outline" className={className} onClick={() => openStudyToolkit(scope)}>
      <NotebookPen className="h-4 w-4" aria-hidden="true" />
      Study Tools
    </Button>
  );
}

export function StudyToolkit() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<ToolkitTab>("whiteboard");
  const [notesScope, setNotesScope] = useState(defaultNotesScope);

  useEffect(() => {
    function handleOpen(event: Event) {
      const customEvent = event as CustomEvent<{ scope?: string }>;
      setNotesScope(customEvent.detail?.scope || defaultNotesScope);
      setIsOpen(true);
    }

    window.addEventListener("open-study-toolkit", handleOpen);
    return () => window.removeEventListener("open-study-toolkit", handleOpen);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  return (
    <>
      <button
        type="button"
        className="fixed bottom-[calc(6.5rem+env(safe-area-inset-bottom))] right-3 z-40 flex min-h-14 items-center gap-2 rounded-full border bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 lg:bottom-5"
        onClick={() => setIsOpen(true)}
      >
        <NotebookPen className="h-4 w-4" aria-hidden="true" />
        Study Tools
      </button>

      {isOpen ? (
        <aside className="fixed inset-0 z-50 h-[100dvh] overflow-hidden bg-card shadow-2xl shadow-primary/20 lg:inset-auto lg:bottom-5 lg:right-5 lg:top-5 lg:h-auto lg:w-[760px] lg:rounded-3xl lg:border">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Study Toolkit</h2>
              <p className="text-xs text-muted-foreground">Scratch space only. Nothing here changes your score.</p>
            </div>
            <Button type="button" variant="outline" size="icon" onClick={() => setIsOpen(false)} aria-label="Close Study Toolkit">
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>

          <div className="flex gap-2 overflow-x-auto border-b px-3 py-2">
            <ToolkitTabButton active={activeTab === "whiteboard"} icon={Pencil} label="Whiteboard" onClick={() => setActiveTab("whiteboard")} />
            <ToolkitTabButton active={activeTab === "calculator"} icon={Calculator} label="Calculators" onClick={() => setActiveTab("calculator")} />
            <ToolkitTabButton active={activeTab === "graph"} icon={FunctionSquare} label="Graph" onClick={() => setActiveTab("graph")} />
            <ToolkitTabButton active={activeTab === "notes"} icon={NotebookPen} label="Notes" onClick={() => setActiveTab("notes")} />
          </div>

          <div className="h-[calc(100dvh-7.5rem)] overscroll-contain overflow-y-auto p-3 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-4 lg:h-[calc(100vh-8rem)]">
            {activeTab === "whiteboard" ? <WhiteboardTool /> : null}
            {activeTab === "calculator" ? <CalculatorTools /> : null}
            {activeTab === "graph" ? <GraphTool /> : null}
            {activeTab === "notes" ? <NotesTool scope={notesScope} /> : null}
          </div>
        </aside>
      ) : null}
    </>
  );
}

function ToolkitTabButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: typeof Pencil;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`flex min-h-11 shrink-0 items-center gap-2 rounded-2xl px-3 text-sm font-medium ${active ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}
      onClick={onClick}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </button>
  );
}

function WhiteboardTool() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const isDrawingRef = useRef(false);
  const lastPointRef = useRef<{ x: number; y: number } | null>(null);
  const [color, setColor] = useState(colors[0].value);
  const [size, setSize] = useState(markerSizes[1].value);
  const [isEraser, setIsEraser] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [redoStack, setRedoStack] = useState<string[]>([]);

  useEffect(() => {
    function resizeCanvas() {
      const canvas = canvasRef.current;
      const wrapper = wrapperRef.current;
      if (!canvas || !wrapper) {
        return;
      }

      const previousImage = canvas.toDataURL("image/png");
      const ratio = window.devicePixelRatio || 1;
      const rect = wrapper.getBoundingClientRect();
      const canvasHeight = Math.round(Math.min(Math.max(window.innerHeight * 0.46, 280), 460));
      canvas.width = Math.max(1, Math.floor(rect.width * ratio));
      canvas.height = Math.floor(canvasHeight * ratio);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${canvasHeight}px`;

      const context = canvas.getContext("2d");
      if (!context) {
        return;
      }
      context.scale(ratio, ratio);
      context.lineCap = "round";
      context.lineJoin = "round";
      context.fillStyle = "white";
      context.fillRect(0, 0, rect.width, canvasHeight);

      if (history.length > 0) {
        restoreImage(previousImage);
      } else {
        saveSnapshot();
      }
    }

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    return () => window.removeEventListener("resize", resizeCanvas);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pointFromEvent(event: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) {
      return { x: 0, y: 0 };
    }
    const rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  function startDrawing(event: React.PointerEvent<HTMLCanvasElement>) {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    isDrawingRef.current = true;
    lastPointRef.current = pointFromEvent(event);
  }

  function draw(event: React.PointerEvent<HTMLCanvasElement>) {
    event.preventDefault();
    if (!isDrawingRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const lastPoint = lastPointRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || !lastPoint) {
      return;
    }

    const nextPoint = pointFromEvent(event);
    context.globalCompositeOperation = isEraser ? "destination-out" : "source-over";
    context.strokeStyle = color;
    context.lineWidth = size;
    context.beginPath();
    context.moveTo(lastPoint.x, lastPoint.y);
    context.lineTo(nextPoint.x, nextPoint.y);
    context.stroke();
    lastPointRef.current = nextPoint;
  }

  function stopDrawing(event?: React.PointerEvent<HTMLCanvasElement>) {
    event?.preventDefault();
    if (event?.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!isDrawingRef.current) {
      return;
    }
    isDrawingRef.current = false;
    lastPointRef.current = null;
    saveSnapshot();
  }

  function saveSnapshot() {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const snapshot = canvas.toDataURL("image/png");
    setHistory((currentHistory) => [...currentHistory.slice(-14), snapshot]);
    setRedoStack([]);
  }

  function restoreImage(dataUrl: string) {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }
    const image = new Image();
    image.onload = () => {
      context.globalCompositeOperation = "source-over";
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width / (window.devicePixelRatio || 1), canvas.height / (window.devicePixelRatio || 1));
    };
    image.src = dataUrl;
  }

  function clearBoard() {
    const confirmed = window.confirm("Clear the whiteboard?");
    if (!confirmed) {
      return;
    }

    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }
    const rect = canvas.getBoundingClientRect();
    context.globalCompositeOperation = "source-over";
    context.fillStyle = "white";
    context.fillRect(0, 0, rect.width, rect.height);
    saveSnapshot();
  }

  function undo() {
    if (history.length <= 1) {
      return;
    }
    const nextHistory = history.slice(0, -1);
    const current = history[history.length - 1];
    const previous = nextHistory[nextHistory.length - 1];
    setHistory(nextHistory);
    setRedoStack((currentRedoStack) => [current, ...currentRedoStack]);
    restoreImage(previous);
  }

  function redo() {
    const [next, ...remaining] = redoStack;
    if (!next) {
      return;
    }
    setRedoStack(remaining);
    setHistory((currentHistory) => [...currentHistory, next]);
    restoreImage(next);
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:flex sm:flex-wrap sm:items-center">
        <div className="flex min-h-12 items-center gap-2 rounded-2xl border bg-background px-3 py-2">
          <Palette className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {colors.map((swatch) => (
            <button
              key={swatch.value}
              type="button"
              className={`h-9 w-9 rounded-full border-2 ${color === swatch.value && !isEraser ? "border-foreground" : "border-transparent"}`}
              style={{ backgroundColor: swatch.value }}
              onClick={() => {
                setColor(swatch.value);
                setIsEraser(false);
              }}
              aria-label={`Use ${swatch.label} marker`}
            />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-2xl border bg-background p-2">
          {markerSizes.map((markerSize) => (
            <button
              key={markerSize.label}
              type="button"
              className={`min-h-11 rounded-xl px-2 text-xs font-medium ${size === markerSize.value ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}
              onClick={() => setSize(markerSize.value)}
            >
              {markerSize.label}
            </button>
          ))}
        </div>
        <Button type="button" className="min-h-11 w-full sm:w-auto" variant={isEraser ? "secondary" : "outline"} onClick={() => setIsEraser((current) => !current)}>
          <Eraser className="h-4 w-4" aria-hidden="true" />
          Eraser
        </Button>
        <Button type="button" className="min-h-11 w-full sm:w-auto" variant="outline" onClick={undo} disabled={history.length <= 1}>
          <Undo2 className="h-4 w-4" aria-hidden="true" />
          Undo
        </Button>
        <Button type="button" className="min-h-11 w-full sm:w-auto" variant="outline" onClick={redo} disabled={redoStack.length === 0}>
          <Redo2 className="h-4 w-4" aria-hidden="true" />
          Redo
        </Button>
        <Button type="button" className="min-h-11 w-full sm:w-auto" variant="outline" onClick={clearBoard}>
          <Trash2 className="h-4 w-4" aria-hidden="true" />
          Clear
        </Button>
      </div>
      <div ref={wrapperRef} className="overscroll-contain overflow-hidden rounded-2xl border bg-white shadow-inner touch-none">
        <canvas
          ref={canvasRef}
          className="block touch-none select-none"
          style={{ touchAction: "none" }}
          aria-label="Whiteboard drawing space"
          onPointerDown={startDrawing}
          onPointerMove={draw}
          onPointerUp={stopDrawing}
          onPointerCancel={stopDrawing}
          onPointerLeave={stopDrawing}
        />
      </div>
    </div>
  );
}

function CalculatorTools() {
  const [mode, setMode] = useState<CalculatorMode>("basic");
  const [expression, setExpression] = useState("");
  const [result, setResult] = useState("0");

  function calculate() {
    try {
      const value = evaluate(expression || "0");
      setResult(String(value));
    } catch {
      setResult("Check the expression");
    }
  }

  function append(value: string) {
    setExpression((currentExpression) => `${currentExpression}${value}`);
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(["basic", "scientific", "financial"] as CalculatorMode[]).map((item) => (
          <button
            key={item}
            type="button"
            className={`min-h-11 rounded-2xl px-3 text-sm font-medium capitalize ${mode === item ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}
            onClick={() => setMode(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {mode === "financial" ? <FinancialCalculator /> : (
      <div className="space-y-3">
        <label className="block text-sm font-medium">
          Expression
          <input
            className="mt-2 min-h-11 w-full rounded-2xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={expression}
            onChange={(event) => setExpression(event.target.value)}
            placeholder={mode === "scientific" ? "sqrt(49) + sin(0.5)" : "12 * 4 + 8"}
          />
        </label>
        <div className="rounded-2xl border bg-background p-4">
          <p className="text-xs text-muted-foreground">Result</p>
          <p className="mt-1 break-words text-2xl font-semibold">{result}</p>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {calculatorKeys(mode).map((key) => (
            <button key={key.label} type="button" className="min-h-14 rounded-2xl border bg-background text-sm font-semibold" onClick={() => append(key.value)}>
              {key.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Button type="button" onClick={calculate}>Calculate</Button>
          <Button type="button" variant="outline" onClick={() => { setExpression(""); setResult("0"); }}>Clear</Button>
        </div>
      </div>
      )}
    </div>
  );
}

function calculatorKeys(mode: CalculatorMode): Array<{ label: string; value: string }> {
  const basic = ["7", "8", "9", "/", "4", "5", "6", "*", "1", "2", "3", "-", "0", ".", "(", ")", "+"].map((key) => ({ label: key, value: key }));
  if (mode === "scientific") {
    return [
      ...basic,
      { label: "^", value: "^" },
      { label: "x^2", value: "^2" },
      { label: "sqrt", value: "sqrt(" },
      { label: "sin", value: "sin(" },
      { label: "cos", value: "cos(" },
      { label: "tan", value: "tan(" },
      { label: "log", value: "log10(" },
      { label: "ln", value: "log(" }
    ];
  }
  return basic;
}

function FinancialCalculator() {
  const [financialMode, setFinancialMode] = useState<FinancialMode>("simple_interest");
  const [principal, setPrincipal] = useState("1000");
  const [rate, setRate] = useState("5");
  const [time, setTime] = useState("3");
  const [frequency, setFrequency] = useState("12");

  const calculation = calculateFinancialValue({
    financialMode,
    principal: Number(principal),
    ratePercent: Number(rate),
    time: Number(time),
    frequency: Number(frequency)
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        {financialModes.map((modeOption) => (
          <button
            key={modeOption.value}
            type="button"
            className={`min-h-11 rounded-2xl px-3 text-sm font-medium ${financialMode === modeOption.value ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}
            onClick={() => setFinancialMode(modeOption.value)}
          >
            {modeOption.label}
          </button>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <FinancialInput
          label={financialMode === "present_value" ? "Future value" : financialMode === "future_value" ? "Present value" : "Principal"}
          value={principal}
          onChange={setPrincipal}
        />
        <FinancialInput label="Rate per year (%)" value={rate} onChange={setRate} />
        <FinancialInput label="Time (years)" value={time} onChange={setTime} />
        {financialMode === "compound_interest" ? (
          <FinancialInput label="Compounding times per year" value={frequency} onChange={setFrequency} />
        ) : null}
      </div>

      <div className="rounded-2xl border bg-background p-4">
        <p className="text-xs font-medium text-muted-foreground">Formula</p>
        <p className="mt-1 text-sm font-semibold">{calculation.formula}</p>
        <p className="mt-4 text-xs font-medium text-muted-foreground">Result</p>
        <p className="mt-1 text-3xl font-semibold">{calculation.result}</p>
        <p className="mt-2 text-xs text-muted-foreground">{calculation.description}</p>
      </div>
    </div>
  );
}

function FinancialInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <input
        className="mt-2 min-h-11 w-full rounded-2xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

const financialModes: Array<{ label: string; value: FinancialMode }> = [
  { label: "Simple interest", value: "simple_interest" },
  { label: "Compound interest", value: "compound_interest" },
  { label: "Present value", value: "present_value" },
  { label: "Future value", value: "future_value" }
];

function GraphTool() {
  const [graphExpression, setGraphExpression] = useState("y = x^2");
  const plotResult = useMemo(() => prepareFunctionPlot(graphExpression), [graphExpression]);

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium">
        Enter y = expression in x
        <input
          className="mt-2 min-h-11 w-full rounded-2xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          value={graphExpression}
          onChange={(event) => setGraphExpression(event.target.value)}
          placeholder="y = sin(x)"
        />
      </label>
      <div className="h-72 rounded-2xl border bg-background p-2">
        {plotResult.ok ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 12, right: 18, bottom: 12, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" domain={[-10, 10]} tickCount={7} type="number" allowDataOverflow />
              <YAxis domain={["auto", "auto"]} tickCount={5} type="number" width={42} />
              <ReferenceLine x={0} stroke="hsl(var(--foreground))" strokeOpacity={0.45} />
              <ReferenceLine y={0} stroke="hsl(var(--foreground))" strokeOpacity={0.45} />
              <Tooltip formatter={(value) => [Number(value).toFixed(3), "y"]} labelFormatter={(label) => `x = ${Number(label).toFixed(3)}`} />
              {plotResult.segments.map((segment, index) => (
                <Line key={`${plotResult.expression}-${index}`} data={segment} dataKey="y" dot={false} isAnimationActive={false} stroke="hsl(var(--primary))" strokeWidth={2.5} type="monotone" />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="p-4 text-sm text-muted-foreground">Try a simple function like y = x^2, y = sin(x), or y = sqrt(x).</p>
        )}
      </div>
    </div>
  );
}

function NotesTool({ scope }: { scope: string }) {
  const [scratchNotes, setScratchNotes] = useStoredText(`abbot_study_scratch_notes_${scope}`);

  return (
    <div className="grid gap-4">
      <label className="block text-sm font-medium">
        Scratch notes
        <textarea
          className="mt-2 min-h-52 w-full resize-y rounded-2xl border bg-background px-3 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-ring"
          value={scratchNotes}
          onChange={(event) => setScratchNotes(event.target.value)}
          placeholder="Work through ideas, reminders, or rough steps here."
        />
      </label>
      <div className="rounded-2xl bg-muted p-3 text-xs text-muted-foreground">
        Notes are saved in this browser only and scoped to the current concept when opened from a lesson.
      </div>
    </div>
  );
}

function useStoredText(key: string): [string, (value: string) => void] {
  const [value, setValue] = useState("");

  useEffect(() => {
    setValue(window.localStorage.getItem(key) ?? "");
  }, [key]);

  function updateValue(nextValue: string) {
    setValue(nextValue);
    window.localStorage.setItem(key, nextValue);
  }

  return [value, updateValue];
}
