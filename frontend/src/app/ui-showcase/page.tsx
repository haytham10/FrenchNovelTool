"use client";

/**
 * UI Showcase Page
 * Demonstrates all UI primitives and design tokens
 * For testing and documentation purposes
 */

import React, { useState } from 'react';
import { Container, Typography, Box } from '@mui/material';
import { 
  Button, 
  Input, 
  Card, 
  Badge, 
  IconButton, 
  Select, 
  Slider, 
  Section,
  CardSkeleton,
  TableSkeleton,
  TextSkeleton,
  type SelectOption
} from '@/components/ui';
import { Heart, Star, Settings } from 'lucide-react';
import Icon from '@/components/Icon';

export default function UIShowcasePage() {
  const [sliderValue, setSliderValue] = useState(50);
  const [selectValue, setSelectValue] = useState('option1');
  const [inputValue, setInputValue] = useState('');

  const selectOptions: SelectOption[] = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3' },
    { value: 'option4', label: 'Option 4 (Disabled)', disabled: true },
  ];

  return (
    <Box sx={{ py: 8, minHeight: '100vh' }}>
      <Container maxWidth="lg">
        <Typography variant="h1" gutterBottom className="gradient-text">
          UI Components Showcase
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          A demonstration of all available UI primitives and design tokens
        </Typography>

        {/* Buttons Section */}
        <Section title="Buttons" subtitle="Various button styles and states">
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="danger">Danger Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="primary" loading>Loading...</Button>
            <Button variant="primary" disabled>Disabled</Button>
            <Button variant="primary" startIcon={<Icon icon={Star} />}>
              With Icon
            </Button>
          </Box>
        </Section>

        {/* Icon Buttons Section */}
        <Section title="Icon Buttons" subtitle="Icon-only buttons with tooltips">
          <Box sx={{ display: 'flex', gap: 2 }}>
            <IconButton title="Like" aria-label="Like">
              <Icon icon={Heart} />
            </IconButton>
            <IconButton title="Favorite" aria-label="Favorite">
              <Icon icon={Star} />
            </IconButton>
            <IconButton title="Settings" aria-label="Settings">
              <Icon icon={Settings} />
            </IconButton>
          </Box>
        </Section>

        {/* Inputs Section */}
        <Section title="Inputs" subtitle="Text input fields with various states">
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 3 }}>
            <Input
              label="Default Input"
              placeholder="Enter text..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              fullWidth
            />
            <Input
              label="With Helper Text"
              helperText="This is helper text"
              placeholder="Enter text..."
              fullWidth
            />
            <Input
              label="Error State"
              error
              helperText="This field has an error"
              placeholder="Enter text..."
              fullWidth
            />
            <Input
              label="Disabled"
              disabled
              placeholder="Disabled input"
              fullWidth
            />
          </Box>
        </Section>

        {/* Select Section */}
        <Section title="Select" subtitle="Dropdown select components">
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 3 }}>
            <Select
              label="Choose Option"
              options={selectOptions}
              value={selectValue}
              onChange={(e) => setSelectValue(e.target.value as string)}
              fullWidth
            />
            <Select
              label="With Helper Text"
              options={selectOptions}
              value={selectValue}
              onChange={(e) => setSelectValue(e.target.value as string)}
              helperText="Select an option from the list"
              fullWidth
            />
          </Box>
        </Section>

        {/* Slider Section */}
        <Section title="Slider" subtitle="Range slider components">
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 3 }}>
            <Slider
              label="Volume"
              showValue
              value={sliderValue}
              onChange={(_, value) => setSliderValue(value as number)}
              min={0}
              max={100}
              aria-label="Volume"
            />
            <Slider
              label="With Custom Format"
              showValue
              value={sliderValue}
              onChange={(_, value) => setSliderValue(value as number)}
              min={0}
              max={100}
              valueFormatter={(val) => `${val}%`}
              aria-label="Percentage"
            />
          </Box>
        </Section>

        {/* Badges Section */}
        <Section title="Badges" subtitle="Status indicators and labels">
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Badge variant="default" label="Default" />
            <Badge variant="success" label="Success" />
            <Badge variant="error" label="Error" />
            <Badge variant="warning" label="Warning" />
            <Badge variant="info" label="Info" />
          </Box>
        </Section>

        {/* Cards Section */}
        <Section title="Cards" subtitle="Container components">
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' }, gap: 3 }}>
            <Card>
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Default Card
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  A simple card component with default styling
                </Typography>
              </Box>
            </Card>
            <Card hover>
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Hover Card
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  This card has a hover effect
                </Typography>
              </Box>
            </Card>
            <Card elevation={6}>
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Elevated Card
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Higher elevation shadow
                </Typography>
              </Box>
            </Card>
          </Box>
        </Section>

        {/* Skeleton Loaders Section */}
        <Section title="Skeleton Loaders" subtitle="Loading state indicators">
          <Typography variant="h6" gutterBottom>
            Text Skeleton
          </Typography>
          <TextSkeleton lines={3} width={['100%', '80%', '60%']} />
          
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            Card Skeleton
          </Typography>
          <CardSkeleton count={2} height={150} />
          
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            Table Skeleton
          </Typography>
          <TableSkeleton rows={3} columns={4} />
        </Section>

        {/* Typography Scale */}
        <Section title="Typography Scale" subtitle="Design token typography examples">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h1">Heading 1</Typography>
            <Typography variant="h2">Heading 2</Typography>
            <Typography variant="h3">Heading 3</Typography>
            <Typography variant="h4">Heading 4</Typography>
            <Typography variant="h5">Heading 5</Typography>
            <Typography variant="h6">Heading 6</Typography>
            <Typography variant="subtitle1">Subtitle 1</Typography>
            <Typography variant="body1">Body 1 - Regular paragraph text</Typography>
            <Typography variant="body2">Body 2 - Smaller paragraph text</Typography>
          </Box>
        </Section>
      </Container>
    </Box>
  );
}
