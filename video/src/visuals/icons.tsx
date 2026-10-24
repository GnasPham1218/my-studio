import React from "react";

export const ChipIcon: React.FC<{ size?: number; color: string }> = ({
  size = 56,
  color,
}) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    <rect
      x="12"
      y="12"
      width="24"
      height="24"
      rx="5"
      stroke={color}
      strokeWidth="2.4"
    />
    <rect x="20" y="20" width="8" height="8" rx="2" fill={color} />
    {[18, 24, 30].map((v) => (
      <React.Fragment key={v}>
        <path d={`M${v} 12V6`} stroke={color} strokeWidth="2.2" strokeLinecap="round" />
        <path d={`M${v} 42v-6`} stroke={color} strokeWidth="2.2" strokeLinecap="round" />
        <path d={`M12 ${v}H6`} stroke={color} strokeWidth="2.2" strokeLinecap="round" />
        <path d={`M42 ${v}h-6`} stroke={color} strokeWidth="2.2" strokeLinecap="round" />
      </React.Fragment>
    ))}
  </svg>
);

export const CloudIcon: React.FC<{ size?: number; color: string }> = ({
  size = 64,
  color,
}) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <path
      d="M20 46h26a11 11 0 0 0 1-21.9A16 16 0 0 0 16.7 28 9 9 0 0 0 20 46Z"
      stroke={color}
      strokeWidth="2.6"
      strokeLinejoin="round"
    />
  </svg>
);

export const PhoneIcon: React.FC<{ size?: number; color: string }> = ({
  size = 64,
  color,
}) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <rect
      x="18"
      y="7"
      width="28"
      height="50"
      rx="6"
      stroke={color}
      strokeWidth="2.6"
    />
    <path d="M28 11h8" stroke={color} strokeWidth="2.4" strokeLinecap="round" />
    <rect x="24" y="26" width="16" height="12" rx="3" stroke={color} strokeWidth="2.2" />
  </svg>
);

export const DiskIcon: React.FC<{ size?: number; color: string }> = ({
  size = 64,
  color,
}) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <rect x="12" y="14" width="40" height="36" rx="6" stroke={color} strokeWidth="2.6" />
    <circle cx="32" cy="32" r="9" stroke={color} strokeWidth="2.4" />
    <circle cx="32" cy="32" r="2.2" fill={color} />
  </svg>
);

export const MemoryIcon: React.FC<{ size?: number; color: string }> = ({
  size = 64,
  color,
}) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <rect x="14" y="20" width="36" height="24" rx="4" stroke={color} strokeWidth="2.6" />
    {[22, 30, 38, 46].map((x) => (
      <path
        key={x}
        d={`M${x} 20v-6M${x} 44v6`}
        stroke={color}
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    ))}
  </svg>
);
