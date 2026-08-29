# Design System

## Principles
The UI must feel like a premium professional filmmaking tool, not a generic AI dashboard.
- Restrained visual language.
- Professional data visualization.
- High information density without clutter.

## Typography
- Use modern, highly readable fonts (e.g., Inter, Roboto, or Outfit).
- Clear hierarchy for headings, body, and metadata.

## Spacing & Layout
- Use consistent spacing scales (e.g., 4px baseline).
- Three-column layout for the main script view:
  - Left: Scene Navigator
  - Center: Screenplay Text
  - Right: Findings/Autopsy
- Responsive behavior: Tables and timelines must not overflow unpredictably. Primary focus is desktop.

## Components (shadcn/ui based)
- Subtle borders rather than heavy drop shadows.
- Meaningful color:
  - Critical/Errors: Muted, clear reds.
  - Warnings: Amber/yellow.
  - Info/Resolved: Muted blue/gray.
- Avoid glowing effects or excessive animations. Smooth transitions only where functional.

## States
- Excellent empty, loading, and error states.
- Polished scene continuity heatmap/timeline.
