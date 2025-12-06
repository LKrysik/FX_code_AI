# StateOverviewTable - Visual Testing Guide

## Visual States to Verify

### 1. Empty State
**Expected:** Table shows centered message "No active instances"

```tsx
<StateOverviewTable
  sessionId="test-123"
  instances={[]}
  isLoading={false}
/>
```

**Screenshot checklist:**
- [ ] Message is centered
- [ ] Secondary text appears below main message
- [ ] No table rows visible
- [ ] Footer shows "0 instances"

---

### 2. Loading State
**Expected:** Skeleton loaders in table rows

```tsx
<StateOverviewTable
  sessionId="test-123"
  instances={[]}
  isLoading={true}
/>
```

**Screenshot checklist:**
- [ ] 5 skeleton rows visible
- [ ] Skeletons animate (shimmer effect)
- [ ] Column headers still visible
- [ ] No "empty state" message

---

### 3. Standard Data View
**Expected:** Table populated with mixed states

```tsx
const instances = [
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'BTCUSDT',
    state: 'MONITORING',
    since: new Date(Date.now() - 10 * 60 * 1000).toISOString()
  },
  // ... more instances
];

<StateOverviewTable
  sessionId="test-123"
  instances={instances}
/>
```

**Screenshot checklist:**
- [ ] All 5 columns visible (Strategy, Symbol, State, Since, Action)
- [ ] State badges show correct colors
- [ ] Time display updates every second
- [ ] Footer shows correct count
- [ ] Rows have hover effect

---

### 4. POSITION_ACTIVE State
**Expected:** Row has light red background

```tsx
const instances = [{
  strategy_id: 'pump_dump_v1',
  symbol: 'BTCUSDT',
  state: 'POSITION_ACTIVE',
  since: new Date(Date.now() - 5 * 60 * 1000).toISOString()
}];
```

**Screenshot checklist:**
- [ ] Row background is light red (error.main alpha 0.08)
- [ ] StateBadge shows red "In Position" chip
- [ ] Time displays as "5m Xs"
- [ ] Hover effect darkens the red background
- [ ] Row appears at TOP of table (priority sort)

---

### 5. SIGNAL_DETECTED State
**Expected:** Row has light yellow background, pulsing badge

```tsx
const instances = [{
  strategy_id: 'pump_dump_v1',
  symbol: 'ETHUSDT',
  state: 'SIGNAL_DETECTED',
  since: new Date(Date.now() - 2 * 60 * 1000).toISOString()
}];
```

**Screenshot checklist:**
- [ ] Row background is light yellow (warning.main alpha 0.08)
- [ ] StateBadge shows orange "Signal" chip with pulse animation
- [ ] Time displays as "2m Xs"
- [ ] Hover effect darkens the yellow background
- [ ] Row appears SECOND in priority (after POSITION_ACTIVE)

---

### 6. Mixed States - Priority Sorting
**Expected:** States sorted by priority

```tsx
const instances = [
  { strategy_id: 's1', symbol: 'A', state: 'INACTIVE', since: '2025-12-06T10:00:00Z' },
  { strategy_id: 's1', symbol: 'B', state: 'POSITION_ACTIVE', since: '2025-12-06T10:05:00Z' },
  { strategy_id: 's1', symbol: 'C', state: 'MONITORING', since: '2025-12-06T10:10:00Z' },
  { strategy_id: 's1', symbol: 'D', state: 'SIGNAL_DETECTED', since: '2025-12-06T10:15:00Z' },
];
```

**Screenshot checklist:**
- [ ] Order is: POSITION_ACTIVE → SIGNAL_DETECTED → MONITORING → INACTIVE
- [ ] Symbol B (POSITION_ACTIVE) is first
- [ ] Symbol D (SIGNAL_DETECTED) is second
- [ ] Symbol C (MONITORING) is third
- [ ] Symbol A (INACTIVE) is fourth

---

### 7. No Timestamp (null since)
**Expected:** Displays "N/A" in Since column

```tsx
const instances = [{
  strategy_id: 'test',
  symbol: 'TESTUSDT',
  state: 'INACTIVE',
  since: null
}];
```

**Screenshot checklist:**
- [ ] Since column shows "N/A"
- [ ] No "undefined" or error messages
- [ ] StateBadge still renders correctly

---

### 8. Responsive Design - Mobile View
**Expected:** Table scrolls horizontally

**Screenshot checklist:**
- [ ] Table has horizontal scrollbar on mobile
- [ ] All columns remain readable
- [ ] "View" buttons remain accessible
- [ ] Header text not truncated

---

### 9. Multiple Strategies
**Expected:** Grouped visually (alphabetically sorted)

```tsx
const instances = [
  { strategy_id: 'pump_dump_v1', symbol: 'BTC', state: 'MONITORING', since: '2025-12-06T10:00:00Z' },
  { strategy_id: 'pump_dump_v1', symbol: 'ETH', state: 'MONITORING', since: '2025-12-06T10:00:00Z' },
  { strategy_id: 'scalping_v2', symbol: 'BTC', state: 'MONITORING', since: '2025-12-06T10:00:00Z' },
];
```

**Screenshot checklist:**
- [ ] Same priority states are grouped by strategy_id
- [ ] Within same strategy, sorted by symbol
- [ ] Visual separation clear between different strategies

---

### 10. Long Running Instance
**Expected:** Time displays days/hours format

```tsx
const instances = [{
  strategy_id: 'test',
  symbol: 'BTCUSDT',
  state: 'MONITORING',
  since: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString() // 3 days ago
}];
```

**Screenshot checklist:**
- [ ] Since displays "3d Xh" format
- [ ] No overflow or text truncation
- [ ] Updates correctly every second

---

## Browser Testing Matrix

| Browser | Version | Desktop | Mobile | Notes |
|---------|---------|---------|--------|-------|
| Chrome  | 120+    | ✓       | ✓      | Primary |
| Firefox | 120+    | ✓       | ✓      | |
| Safari  | 17+     | ✓       | ✓      | Check MUI compatibility |
| Edge    | 120+    | ✓       | ✓      | |

---

## Accessibility Testing

### Keyboard Navigation
- [ ] Tab through all "View" buttons
- [ ] Enter key activates "View" button
- [ ] Arrow keys navigate table (if supported by MUI)

### Screen Reader
- [ ] Table headers announced correctly
- [ ] Row data readable in logical order
- [ ] State badges have proper ARIA labels

### Color Contrast
- [ ] Light red background meets WCAG AA for text contrast
- [ ] Light yellow background meets WCAG AA for text contrast
- [ ] StateBadge colors are readable

---

## Performance Testing

### Large Datasets
Test with varying instance counts:

- [ ] 10 instances: < 50ms render
- [ ] 50 instances: < 200ms render
- [ ] 100 instances: < 500ms render
- [ ] 500 instances: Consider virtualization warning

### Real-time Updates
- [ ] Time updates every second without visible lag
- [ ] State changes reflect immediately (via WebSocket)
- [ ] No memory leaks after 1 hour of continuous updates

---

## Common Issues to Check

1. **Time display doesn't update**
   - Check useEffect cleanup
   - Verify interval is set correctly

2. **Sorting doesn't work**
   - Verify STATE_PRIORITY object
   - Check useMemo dependencies

3. **Background colors not showing**
   - Verify theme is provided
   - Check alpha() function usage

4. **Click handler fires twice**
   - Check event.stopPropagation() in button click
   - Verify row and button handlers

5. **Loading state stuck**
   - Verify isLoading prop updates
   - Check API error handling

---

## Visual Regression Testing

If using visual regression tools (e.g., Percy, Chromatic):

```bash
# Take baseline screenshots
npm run test:visual -- --update-snapshots

# Compare against baseline
npm run test:visual
```

Expected screenshot coverage:
- Empty state
- Loading state
- 5 instances (mixed states)
- POSITION_ACTIVE row highlight
- SIGNAL_DETECTED row highlight
- Mobile view
- Hover state (if supported)
