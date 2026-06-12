## ADDED Requirements

### Requirement: Ask Incident chat input has a CSS gradient border
In `PromptChatPanel.tsx`, the `<input>` element in the submit form SHALL be wrapped in a `<div>` that provides a gradient border via `className="p-[1.5px] flex-1 rounded-full bg-gradient-to-r from-blue-500 to-violet-600"`. The input SHALL have `border-0 bg-surface-2 outline-none` and `w-full`. The wrapper div SHALL receive `group` and `focus-within:from-blue-400 focus-within:to-violet-500` to indicate focus with a CSS transition. The form row layout (input + Ask button) SHALL remain intact.

#### Scenario: Gradient border visible at rest
- **WHEN** the Ask Incident section is rendered with an active incident
- **THEN** the chat input has a visible blue-to-purple gradient border

#### Scenario: Focus state visually distinct
- **WHEN** the user clicks into the input
- **THEN** the gradient brightens without any JS event handler

#### Scenario: Layout integrity preserved
- **WHEN** the gradient wrapper is applied
- **THEN** the input and Ask button remain on the same row and aligned
