# UI Components Quick Reference Guide

## 🚀 Getting Started

All UI components are available from `@/components/ui`:

```tsx
import { Button, Card, Input, Select, Slider, Badge, IconButton, Section, Skeleton } from '@/components/ui';
```

## 📦 Component Examples

### Button

```tsx
import { Button } from '@/components/ui';

// Primary button
<Button variant="primary">Save</Button>

// Secondary button
<Button variant="secondary">Cancel</Button>

// Danger button
<Button variant="danger">Delete</Button>

// Ghost button
<Button variant="ghost">Learn more</Button>

// With loading state
<Button variant="primary" loading>Processing...</Button>

// With icon
<Button variant="primary" startIcon={<SaveIcon />}>
  Save Changes
</Button>
```

### IconButton

```tsx
import { IconButton } from '@/components/ui';
import { Settings } from 'lucide-react';

<IconButton 
  title="Settings" 
  aria-label="Open settings"
  onClick={handleClick}
>
  <Icon icon={Settings} />
</IconButton>
```

### Input

```tsx
import { Input } from '@/components/ui';

// Basic input
<Input
  label="Email"
  placeholder="Enter your email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  fullWidth
/>

// With error state
<Input
  label="Password"
  type="password"
  error
  helperText="Password must be at least 8 characters"
  fullWidth
/>
```

### Select

```tsx
import { Select, type SelectOption } from '@/components/ui';

const options: SelectOption[] = [
  { value: 'option1', label: 'Option 1' },
  { value: 'option2', label: 'Option 2' },
  { value: 'option3', label: 'Option 3', disabled: true },
];

<Select
  label="Choose an option"
  options={options}
  value={selectedValue}
  onChange={(e) => setSelectedValue(e.target.value)}
  helperText="Select the best option for you"
  fullWidth
/>
```

### Slider

```tsx
import { Slider } from '@/components/ui';

// Basic slider
<Slider
  label="Volume"
  showValue
  value={volume}
  onChange={(_, value) => setVolume(value as number)}
  min={0}
  max={100}
  aria-label="Volume control"
/>

// With custom formatting
<Slider
  label="Percentage"
  showValue
  value={percentage}
  onChange={(_, value) => setPercentage(value as number)}
  valueFormatter={(val) => `${val}%`}
  min={0}
  max={100}
/>
```

### Card

```tsx
import { Card } from '@/components/ui';

// Basic card
<Card>
  <Box sx={{ p: 3 }}>
    <Typography variant="h6">Card Title</Typography>
    <Typography variant="body2">Card content goes here</Typography>
  </Box>
</Card>

// Card with hover effect
<Card hover>
  <Box sx={{ p: 3 }}>
    <Typography variant="h6">Hover Me</Typography>
  </Box>
</Card>

// Card with higher elevation
<Card elevation={6}>
  <Box sx={{ p: 3 }}>
    <Typography variant="h6">Elevated Card</Typography>
  </Box>
</Card>
```

### Badge

```tsx
import { Badge } from '@/components/ui';

<Badge variant="success" label="Active" />
<Badge variant="error" label="Error" />
<Badge variant="warning" label="Pending" />
<Badge variant="info" label="Info" />
<Badge variant="default" label="Default" />
```

### Section/Panel

```tsx
import { Section } from '@/components/ui';

<Section 
  title="User Settings" 
  subtitle="Manage your account preferences"
>
  {/* Section content */}
  <Typography>Your content here</Typography>
</Section>

// Without divider
<Section title="Quick Actions" noDivider>
  {/* Content */}
</Section>
```

### Skeleton Loaders

```tsx
import { CardSkeleton, TableSkeleton, TextSkeleton } from '@/components/ui';

// Loading cards
<CardSkeleton count={3} height={200} />

// Loading table
<TableSkeleton rows={5} columns={4} />

// Loading text
<TextSkeleton lines={3} width={['100%', '80%', '60%']} />
```

## 🎨 Design Tokens

Access design tokens for custom components:

```tsx
import { tokens } from '@/styles/tokens';

// Use tokens in your styles
const customStyles = {
  fontSize: tokens.typography.fontSize.lg,
  padding: tokens.spacing[4],
  borderRadius: tokens.radius.md,
  color: tokens.colors.light.primary,
};
```

## 🎯 Theme System

### Using Theme Context

```tsx
import { useContext } from 'react';
import { ColorModeContext } from '@/components/Providers';

function MyComponent() {
  const { mode, toggle } = useContext(ColorModeContext);
  
  return (
    <button onClick={toggle}>
      Current mode: {mode}
    </button>
  );
}
```

### System Preference Detection

The theme system automatically detects and applies the user's system preference on first load. Users can override this with the theme toggle button.

## ♿ Accessibility Best Practices

All components follow these accessibility guidelines:

1. **Keyboard Navigation**: All interactive elements are keyboard accessible
2. **ARIA Labels**: Use `aria-label` prop for screen readers
3. **Focus Visible**: Focus rings are visible on keyboard navigation
4. **Semantic HTML**: Components use appropriate HTML elements

Example:
```tsx
<Button 
  aria-label="Save document"
  onClick={handleSave}
>
  Save
</Button>

<IconButton 
  title="Settings"
  aria-label="Open settings menu"
  onClick={handleSettings}
>
  <SettingsIcon />
</IconButton>
```

## 📱 Responsive Design

All components are responsive by default. Use MUI's `sx` prop for custom responsive behavior:

```tsx
<Card sx={{ 
  p: { xs: 2, md: 4 },  // 16px on mobile, 32px on desktop
  width: { xs: '100%', md: '50%' }
}}>
  {/* Content */}
</Card>
```

## 🔧 TypeScript Support

All components are fully typed. Import types as needed:

```tsx
import type { 
  ButtonProps, 
  ButtonVariant,
  SelectOption,
  CardProps,
  BadgeVariant 
} from '@/components/ui';
```

## 🎪 UI Showcase

Visit `/ui-showcase` in development to see all components in action with various states and configurations.

## 💡 Tips

1. **Always use fullWidth**: For inputs and selects in forms for consistent layout
2. **Use Section for organization**: Wrap related content in Section components
3. **Leverage skeleton loaders**: Show loading states instead of spinners
4. **Follow the 8px grid**: Use spacing values from `tokens.spacing` for consistency
5. **Test keyboard navigation**: Always verify Tab, Enter, and Space key functionality

## 🐛 Common Issues

### Issue: Focus ring not showing
**Solution**: Ensure you're using `:focus-visible` styles (already included in all components)

### Issue: Theme not persisting
**Solution**: Check that localStorage is available and not blocked

### Issue: Components not rendering
**Solution**: Make sure to import from `@/components/ui`, not individual files

## 📚 Further Reading

- See `docs/UI_OVERHAUL_PHASE_A_SUMMARY.md` for complete implementation details
- Check component source files in `frontend/src/components/ui/` for advanced usage
- Review design tokens in `frontend/src/styles/tokens.ts` for available values
