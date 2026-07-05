import * as React from "react";
import { cn } from "@/lib/cn";

interface SliderProps extends React.InputHTMLAttributes<HTMLInputElement> {
  value: number;
  onValueChange?: (v: number) => void;
}

export const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value, onValueChange, onChange, ...props }, ref) => (
    <input
      ref={ref}
      type="range"
      value={value}
      onChange={(e) => {
        onValueChange?.(Number(e.target.value));
        onChange?.(e);
      }}
      className={cn(
        "h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[var(--c-border-2)] accent-[#7A92F4]",
        "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:shadow",
        className,
      )}
      {...props}
    />
  ),
);
Slider.displayName = "Slider";
