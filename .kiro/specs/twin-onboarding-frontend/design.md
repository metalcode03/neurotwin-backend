# Design Document: Twin Onboarding Frontend

## Overview

The Twin Onboarding Frontend is a multi-step wizard interface that guides new users through creating their cognitive digital twin. The feature implements a progressive disclosure pattern where users move through 10 distinct steps: welcome, three questionnaire sections, model selection, cognitive blend configuration, optional payment, review, creation, and success. The design emphasizes clarity, progress visibility, and seamless integration with existing backend APIs while maintaining the NeuroTwin cognitive OS aesthetic.

The onboarding wizard is triggered when a signed-in user's twin status check (GET /api/v1/twin/) returns a 404 response. The wizard saves progress automatically at each step, allowing users to resume later. For users selecting premium AI models on free tier, the wizard seamlessly integrates a subscription upgrade flow with payment collection before twin creation.

## Architecture

### High-Level Component Structure

```
OnboardingPage (app/onboarding/page.tsx)
├── OnboardingWizard (components/onboarding/OnboardingWizard.tsx)
│   ├── ProgressIndicator (components/onboarding/ProgressIndicator.tsx)
│   ├── WelcomeStep (components/onboarding/steps/WelcomeStep.tsx)
│   ├── QuestionnaireStep (components/onboarding/steps/QuestionnaireStep.tsx)
│   │   ├── SliderQuestion (components/onboarding/questions/SliderQuestion.tsx)
│   │   ├── TextQuestion (components/onboarding/questions/TextQuestion.tsx)
│   │   ├── SelectQuestion (components/onboarding/questions/SelectQuestion.tsx)
│   │   └── TextListQuestion (components/onboarding/questions/TextListQuestion.tsx)
│   ├── ModelSelectionStep (components/onboarding/steps/ModelSelectionStep.tsx)
│   ├── CognitiveBlendStep (components/onboarding/steps/CognitiveBlendStep.tsx)
│   ├── PaymentStep (components/onboarding/steps/PaymentStep.tsx)
│   ├── ReviewStep (components/onboarding/steps/ReviewStep.tsx)
│   ├── CreatingStep (components/onboarding/steps/CreatingStep.tsx)
│   └── SuccessStep (components/onboarding/steps/SuccessStep.tsx)
├── useOnboarding (hooks/useOnboarding.ts)
└── onboardingApi (lib/api/onboarding.ts)
```

### Data Flow

```
User Navigation → OnboardingWizard State → Step Components → User Input
                                                                  ↓
                                                            Validation
                                                                  ↓
                                                         Update Local State
                                                                  ↓
                                                    Save Progress (API Call)
                                                                  ↓
                                                          Advance to Next Step
```


### Routing and Navigation

The onboarding wizard uses client-side routing with URL state management:

- Base route: `/onboarding`
- Step tracking: Query parameter `?step=N` (1-10)
- Navigation: Browser back/forward supported via URL state
- Redirect logic: Middleware checks twin existence and redirects accordingly

### State Management Strategy

The wizard uses React state with the following structure:

```typescript
interface OnboardingState {
  currentStep: number;
  questionnaire: {
    communicationStyle: Record<string, any>;
    decisionPatterns: Record<string, any>;
    preferences: Record<string, any>;
  };
  selectedModel: string | null;
  cognitiveBlend: number;
  isLoading: boolean;
  error: string | null;
  availableModels: AIModel[];
  userTier: SubscriptionTier;
}
```

State persistence occurs at two levels:
1. **Local state**: React state for immediate UI updates
2. **Backend state**: PATCH /api/v1/twin/onboarding/progress after each step completion

## Components and Interfaces

### Core Components

#### OnboardingWizard

The main orchestrator component that manages wizard state, step navigation, and API interactions.

```typescript
interface OnboardingWizardProps {
  initialData?: OnboardingStartResponse;
}

interface OnboardingWizardState {
  currentStep: number;
  questionnaire: QuestionnaireResponses;
  selectedModel: string | null;
  cognitiveBlend: number;
  isLoading: boolean;
  error: string | null;
}

// Key methods
const handleNext = async () => {
  // Validate current step
  // Save progress to backend
  // Advance to next step
};

const handleBack = () => {
  // Navigate to previous step
  // Preserve all entered data
};

const handleStepComplete = async (stepData: any) => {
  // Update local state
  // Call progress API
  // Handle errors
};
```



#### ProgressIndicator

Visual component showing current step and overall progress.

```typescript
interface ProgressIndicatorProps {
  currentStep: number;
  totalSteps: number;
  stepLabels: string[];
}

// Renders:
// - Step numbers with completion status
// - Progress bar showing percentage complete
// - Current step label
```

#### Step Components

Each step is a self-contained component with consistent interface:

```typescript
interface StepProps {
  data: any; // Current step data
  onComplete: (data: any) => void;
  onBack: () => void;
  isLoading: boolean;
}

// All steps implement:
// - Data validation
// - Error display
// - Back/Next navigation
// - Responsive layout
```

### Question Components

Reusable question components for the questionnaire steps:

#### SliderQuestion

```typescript
interface SliderQuestionProps {
  question: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  labels?: { min: string; max: string };
}

// Renders:
// - Question text
// - Range slider (0.0-1.0)
// - Current value display
// - Min/max labels
```

#### SelectQuestion

```typescript
interface SelectQuestionProps {
  question: string;
  options: Array<{ value: string; label: string; description?: string }>;
  value: string | null;
  onChange: (value: string) => void;
  multiSelect?: boolean;
}

// Renders:
// - Question text
// - Selectable cards or dropdown
// - Visual selection state
```

#### TextQuestion

```typescript
interface TextQuestionProps {
  question: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
}
```

#### TextListQuestion

```typescript
interface TextListQuestionProps {
  question: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  maxItems?: number;
}

// Renders:
// - Question text
// - List of text inputs
// - Add/remove buttons
// - Item reordering (optional)
```



### API Integration Layer

#### onboardingApi Module

```typescript
// lib/api/onboarding.ts

interface OnboardingStartResponse {
  status: string;
  questionnaire: {
    sections: {
      communication_style: Question[];
      decision_patterns: Question[];
      preferences: Question[];
    };
  };
  available_models: AIModel[];
  saved_responses?: QuestionnaireResponses;
  selected_model?: string;
  selected_blend?: number;
}

interface Question {
  id: string;
  text: string;
  type: 'slider' | 'text' | 'select' | 'text_list';
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
  required: boolean;
}

interface AIModel {
  id: string;
  name: string;
  description: string;
  tier_required: SubscriptionTier;
  capabilities: string[];
}

interface QuestionnaireResponses {
  communication_style: Record<string, any>;
  decision_patterns: Record<string, any>;
  preferences: Record<string, any>;
}

// API methods
export const onboardingApi = {
  start: async (): Promise<OnboardingStartResponse> => {
    return request('/twin/onboarding/start', { method: 'POST' });
  },

  saveProgress: async (data: {
    responses?: Partial<QuestionnaireResponses>;
    model?: string;
    cognitive_blend?: number;
  }): Promise<void> => {
    return request('/twin/onboarding/progress', {
      method: 'PATCH',
      body: data,
    });
  },

  complete: async (data: {
    responses: QuestionnaireResponses;
    model: string;
    cognitive_blend: number;
  }): Promise<TwinCreationResponse> => {
    return request('/twin/onboarding/complete', {
      method: 'POST',
      body: data,
    });
  },
};
```



### Custom Hook: useOnboarding

```typescript
// hooks/useOnboarding.ts

interface UseOnboardingReturn {
  state: OnboardingState;
  currentStepComponent: React.ComponentType<StepProps>;
  canGoBack: boolean;
  canGoNext: boolean;
  goNext: () => Promise<void>;
  goBack: () => void;
  updateStepData: (data: any) => void;
  isLoading: boolean;
  error: string | null;
}

export function useOnboarding(): UseOnboardingReturn {
  const [state, setState] = useState<OnboardingState>(initialState);
  const router = useRouter();
  const { user } = useAuth();

  // Initialize onboarding data on mount
  useEffect(() => {
    const init = async () => {
      const data = await onboardingApi.start();
      setState(prev => ({
        ...prev,
        availableModels: data.available_models,
        questionnaire: data.saved_responses || {},
        selectedModel: data.selected_model || null,
        cognitiveBlend: data.selected_blend || 50,
      }));
    };
    init();
  }, []);

  // Save progress when step data changes
  const saveProgress = async () => {
    await onboardingApi.saveProgress({
      responses: state.questionnaire,
      model: state.selectedModel,
      cognitive_blend: state.cognitiveBlend,
    });
  };

  // Navigation handlers
  const goNext = async () => {
    await saveProgress();
    setState(prev => ({ ...prev, currentStep: prev.currentStep + 1 }));
    router.push(`/onboarding?step=${state.currentStep + 1}`);
  };

  const goBack = () => {
    setState(prev => ({ ...prev, currentStep: prev.currentStep - 1 }));
    router.push(`/onboarding?step=${state.currentStep - 1}`);
  };

  return {
    state,
    currentStepComponent: getStepComponent(state.currentStep),
    canGoBack: state.currentStep > 1,
    canGoNext: validateCurrentStep(state),
    goNext,
    goBack,
    updateStepData,
    isLoading: state.isLoading,
    error: state.error,
  };
}
```

## Data Models

### TypeScript Interfaces

```typescript
// types/onboarding.ts

export enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  TWIN_PLUS = 'twin_plus',
  EXECUTIVE = 'executive',
}

export interface OnboardingState {
  currentStep: number;
  questionnaire: QuestionnaireResponses;
  selectedModel: string | null;
  cognitiveBlend: number;
  isLoading: boolean;
  error: string | null;
  availableModels: AIModel[];
  userTier: SubscriptionTier;
}

export interface QuestionnaireResponses {
  communication_style: {
    openness?: number;
    extraversion?: number;
    agreeableness?: number;
    formality?: number;
    warmth?: number;
    directness?: number;
    preferred_greeting?: string;
    sign_off_style?: string;
  };
  decision_patterns: {
    conscientiousness?: number;
    risk_tolerance?: number;
    speed_vs_accuracy?: number;
    collaboration_preference?: number;
  };
  preferences: {
    neuroticism?: number;
    humor_level?: number;
    response_length?: 'brief' | 'moderate' | 'detailed';
    emoji_usage?: 'none' | 'minimal' | 'moderate' | 'frequent';
    vocabulary_patterns?: string[];
  };
}

export interface AIModel {
  id: string;
  name: string;
  description: string;
  tier_required: SubscriptionTier;
  capabilities: string[];
  performance_level: 'standard' | 'advanced' | 'premium';
}

export interface TwinCreationResponse {
  id: string;
  user_id: string;
  model: string;
  cognitive_blend: number;
  blend_mode: string;
  requires_confirmation: boolean;
  is_active: boolean;
  created_at: string;
}
```



### Step Flow and Validation

```typescript
// Step configuration
const STEPS = [
  { id: 1, name: 'Welcome', component: WelcomeStep, validate: () => true },
  { id: 2, name: 'Communication', component: QuestionnaireStep, validate: validateCommunicationStyle },
  { id: 3, name: 'Decision Making', component: QuestionnaireStep, validate: validateDecisionPatterns },
  { id: 4, name: 'Preferences', component: QuestionnaireStep, validate: validatePreferences },
  { id: 5, name: 'AI Model', component: ModelSelectionStep, validate: validateModelSelection },
  { id: 6, name: 'Cognitive Blend', component: CognitiveBlendStep, validate: validateBlend },
  { id: 7, name: 'Payment', component: PaymentStep, validate: validatePayment, conditional: true },
  { id: 8, name: 'Review', component: ReviewStep, validate: () => true },
  { id: 9, name: 'Creating', component: CreatingStep, validate: () => true },
  { id: 10, name: 'Success', component: SuccessStep, validate: () => true },
];

// Validation functions
function validateCommunicationStyle(state: OnboardingState): boolean {
  const required = ['openness', 'extraversion', 'agreeableness', 'formality', 
                    'warmth', 'directness', 'preferred_greeting', 'sign_off_style'];
  return required.every(field => 
    state.questionnaire.communication_style[field] !== undefined
  );
}

function validateDecisionPatterns(state: OnboardingState): boolean {
  const required = ['conscientiousness', 'risk_tolerance', 
                    'speed_vs_accuracy', 'collaboration_preference'];
  return required.every(field => 
    state.questionnaire.decision_patterns[field] !== undefined
  );
}

function validatePreferences(state: OnboardingState): boolean {
  const required = ['neuroticism', 'humor_level', 'response_length', 
                    'emoji_usage', 'vocabulary_patterns'];
  return required.every(field => 
    state.questionnaire.preferences[field] !== undefined
  );
}

function validateModelSelection(state: OnboardingState): boolean {
  return state.selectedModel !== null;
}

function validateBlend(state: OnboardingState): boolean {
  return state.cognitiveBlend >= 0 && state.cognitiveBlend <= 100;
}

// Conditional step logic
function shouldShowPaymentStep(state: OnboardingState): boolean {
  if (!state.selectedModel) return false;
  
  const model = state.availableModels.find(m => m.id === state.selectedModel);
  if (!model) return false;
  
  // Show payment if user is on FREE tier and selected model requires PRO+
  return state.userTier === SubscriptionTier.FREE && 
         model.tier_required !== SubscriptionTier.FREE;
}
```



## Detailed Step Designs

### Step 1: Welcome Screen

**Purpose**: Introduce users to the Twin concept and set expectations.

**Layout**:
- Large hero section with Twin illustration/icon
- Headline: "Meet Your Cognitive Twin"
- 3-4 bullet points explaining key capabilities
- "Get Started" CTA button

**Content**:
```
Your Cognitive Twin learns your communication style, decision patterns, 
and personality to act as your AI-powered assistant across all your 
connected platforms.

• Handles communications in your unique voice
• Makes decisions based on your preferences
• Automates tasks while you stay in control
• Learns and adapts over time
```

### Step 2-4: Questionnaire Steps

**Purpose**: Collect personality and preference data for CSM creation.

**Layout**:
- Section title (e.g., "Communication Style")
- Progress within section (Question 1 of 8)
- Question text (large, clear)
- Input control (slider, text, select, etc.)
- Back and Next buttons

**Question Rendering Logic**:
```typescript
function renderQuestion(question: Question, value: any, onChange: (v: any) => void) {
  switch (question.type) {
    case 'slider':
      return <SliderQuestion question={question.text} value={value} onChange={onChange} />;
    case 'text':
      return <TextQuestion question={question.text} value={value} onChange={onChange} />;
    case 'select':
      return <SelectQuestion question={question.text} options={question.options} value={value} onChange={onChange} />;
    case 'text_list':
      return <TextListQuestion question={question.text} values={value} onChange={onChange} />;
  }
}
```

**Section Breakdown**:

**Communication Style (8 questions)**:
1. Openness (slider 0.0-1.0): "How open are you to new ideas?"
2. Extraversion (slider 0.0-1.0): "How outgoing are you in conversations?"
3. Agreeableness (slider 0.0-1.0): "How cooperative are you with others?"
4. Formality (slider 0.0-1.0): "How formal is your communication style?"
5. Warmth (slider 0.0-1.0): "How warm and friendly are your messages?"
6. Directness (slider 0.0-1.0): "How direct are you in communication?"
7. Preferred Greeting (text): "How do you typically greet people?"
8. Sign-off Style (text): "How do you typically end messages?"

**Decision Making (4 questions)**:
1. Conscientiousness (slider 0.0-1.0): "How detail-oriented are you?"
2. Risk Tolerance (slider 0.0-1.0): "How comfortable are you with risk?"
3. Speed vs Accuracy (slider 0.0-1.0): "Do you prefer quick decisions or thorough analysis?"
4. Collaboration Preference (slider 0.0-1.0): "Do you prefer working alone or with others?"

**Personal Preferences (5 questions)**:
1. Neuroticism (slider 0.0-1.0): "How emotionally reactive are you?"
2. Humor Level (slider 0.0-1.0): "How much humor do you use?"
3. Response Length (select): "Brief", "Moderate", "Detailed"
4. Emoji Usage (select): "None", "Minimal", "Moderate", "Frequent"
5. Vocabulary Patterns (text_list): "Common phrases you use"



### Step 5: Model Selection

**Purpose**: Allow users to choose their AI model based on capabilities and tier access.

**Layout**:
- Section title: "Choose Your AI Model"
- Grid of model cards (2 columns on desktop, 1 on mobile)
- Each card shows:
  - Model name
  - Performance badge (Standard/Advanced/Premium)
  - Description
  - Key capabilities (bullet list)
  - Tier requirement badge
  - "Select" button or "Upgrade Required" badge

**Model Card States**:
- **Available**: User's tier allows access → Selectable with purple border on selection
- **Requires Upgrade**: User's tier too low → Grayed out with "Upgrade to PRO" badge
- **Selected**: Currently selected model → Purple background, checkmark icon

**Model Display Logic**:
```typescript
function ModelCard({ model, userTier, selected, onSelect }: ModelCardProps) {
  const isAvailable = canAccessModel(userTier, model.tier_required);
  const requiresUpgrade = !isAvailable;

  return (
    <GlassPanel className={cn(
      'p-6 cursor-pointer transition-all',
      selected && 'bg-purple-700 text-white',
      !isAvailable && 'opacity-50 cursor-not-allowed'
    )}>
      <div className="flex items-start justify-between">
        <h3 className="text-lg font-semibold">{model.name}</h3>
        {selected && <CheckCircle className="text-white" />}
      </div>
      
      <p className="text-sm mt-2">{model.description}</p>
      
      <ul className="mt-4 space-y-2">
        {model.capabilities.map(cap => (
          <li key={cap} className="text-sm flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            {cap}
          </li>
        ))}
      </ul>
      
      {requiresUpgrade ? (
        <div className="mt-4 px-3 py-1 bg-purple-300 text-purple-700 rounded-full text-xs inline-block">
          Requires {model.tier_required.toUpperCase()}
        </div>
      ) : (
        <button
          onClick={() => onSelect(model.id)}
          className="mt-4 w-full py-2 bg-purple-700 text-white rounded-lg hover:bg-purple-600"
        >
          {selected ? 'Selected' : 'Select Model'}
        </button>
      )}
    </GlassPanel>
  );
}
```

**Available Models**:
- **gemini-3-flash** (FREE): Fast, efficient, good for basic tasks
- **qwen** (FREE): Open-source, privacy-focused
- **mistral** (FREE): Balanced performance and speed
- **gemini-3-pro** (PRO+): Advanced reasoning, best performance



### Step 6: Cognitive Blend Configuration

**Purpose**: Set the balance between AI logic and personality mimicry.

**Layout**:
- Section title: "Set Your Cognitive Blend"
- Explanation text
- Large slider (0-100)
- Current value display (large number with %)
- Three zone descriptions with visual indicators
- Confirmation notice for high blend values

**Blend Zones**:
```typescript
const BLEND_ZONES = [
  {
    range: [0, 30],
    label: 'Pure AI Logic',
    description: 'Your Twin uses minimal personality, focusing on efficient, logical responses.',
    color: 'blue',
    icon: Brain,
  },
  {
    range: [31, 70],
    label: 'Balanced',
    description: 'Your Twin blends your personality with AI reasoning for natural, effective communication.',
    color: 'purple',
    icon: Scale,
  },
  {
    range: [71, 100],
    label: 'Heavy Personality',
    description: 'Your Twin closely mimics your style. Actions will require your confirmation.',
    color: 'pink',
    icon: User,
    requiresConfirmation: true,
  },
];

function getBlendZone(value: number) {
  return BLEND_ZONES.find(zone => 
    value >= zone.range[0] && value <= zone.range[1]
  );
}
```

**Component Structure**:
```typescript
function CognitiveBlendStep({ data, onComplete }: StepProps) {
  const [blend, setBlend] = useState(data.cognitiveBlend || 50);
  const zone = getBlendZone(blend);

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Set Your Cognitive Blend</h2>
      <p className="text-neutral-700 mb-8">
        Control how much your Twin uses your personality versus pure AI logic.
      </p>

      <div className="mb-8">
        <div className="text-6xl font-bold text-center text-purple-700 mb-4">
          {blend}%
        </div>
        
        <input
          type="range"
          min="0"
          max="100"
          value={blend}
          onChange={(e) => setBlend(Number(e.target.value))}
          className="w-full h-3 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full"
        />
      </div>

      <GlassPanel className={`p-6 border-2 border-${zone.color}-500`}>
        <div className="flex items-center gap-3 mb-3">
          <zone.icon className={`w-6 h-6 text-${zone.color}-600`} />
          <h3 className="text-lg font-semibold">{zone.label}</h3>
        </div>
        <p className="text-neutral-700">{zone.description}</p>
        
        {zone.requiresConfirmation && (
          <div className="mt-4 p-3 bg-yellow-100 border border-yellow-400 rounded-lg">
            <p className="text-sm text-yellow-800">
              ⚠️ At this blend level, your Twin will require confirmation before taking actions.
            </p>
          </div>
        )}
      </GlassPanel>
    </div>
  );
}
```



### Step 7: Payment (Conditional)

**Purpose**: Collect payment information for subscription upgrade when user selects premium model.

**Conditional Display**: Only shown when:
- User is on FREE tier
- Selected model requires PRO or higher tier

**Layout**:
- Section title: "Upgrade to PRO"
- Tier comparison (FREE vs PRO features)
- Pricing display
- Payment form (card details)
- Secure payment badge
- Terms and conditions checkbox

**Component Structure**:
```typescript
function PaymentStep({ data, onComplete }: StepProps) {
  const [cardDetails, setCardDetails] = useState({
    number: '',
    expiry: '',
    cvc: '',
    name: '',
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      // Call subscription upgrade API
      await api.subscription.upgrade(SubscriptionTier.PRO);
      
      // Update user tier in state
      onComplete({ upgraded: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Upgrade to PRO</h2>
      
      <GlassPanel className="p-6 mb-6">
        <h3 className="font-semibold mb-4">PRO Features</h3>
        <ul className="space-y-2">
          <li className="flex items-center gap-2">
            <CheckCircle className="text-green-500" />
            Access to Gemini-3 Pro model
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle className="text-green-500" />
            Cognitive learning capabilities
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle className="text-green-500" />
            50 autonomous workflows per month
          </li>
        </ul>
        
        <div className="mt-6 text-3xl font-bold text-purple-700">
          $29/month
        </div>
      </GlassPanel>

      <GlassPanel className="p-6">
        <h3 className="font-semibold mb-4">Payment Details</h3>
        
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Card Number"
            value={cardDetails.number}
            onChange={(e) => setCardDetails({ ...cardDetails, number: e.target.value })}
            className="w-full px-4 py-2 border border-neutral-400 rounded-lg"
          />
          
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="MM/YY"
              value={cardDetails.expiry}
              onChange={(e) => setCardDetails({ ...cardDetails, expiry: e.target.value })}
              className="px-4 py-2 border border-neutral-400 rounded-lg"
            />
            <input
              type="text"
              placeholder="CVC"
              value={cardDetails.cvc}
              onChange={(e) => setCardDetails({ ...cardDetails, cvc: e.target.value })}
              className="px-4 py-2 border border-neutral-400 rounded-lg"
            />
          </div>
          
          <input
            type="text"
            placeholder="Cardholder Name"
            value={cardDetails.name}
            onChange={(e) => setCardDetails({ ...cardDetails, name: e.target.value })}
            className="w-full px-4 py-2 border border-neutral-400 rounded-lg"
          />
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-400 rounded-lg text-red-800">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={isProcessing}
          className="mt-6 w-full py-3 bg-purple-700 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
        >
          {isProcessing ? 'Processing...' : 'Upgrade Now'}
        </button>
        
        <p className="mt-4 text-xs text-neutral-600 text-center">
          🔒 Secure payment processing. Cancel anytime.
        </p>
      </GlassPanel>
    </div>
  );
}
```

**Note**: In production, this would integrate with Stripe or similar payment processor. For MVP, this can be a placeholder that simulates the upgrade.



### Step 8: Review and Confirmation

**Purpose**: Display all selections for user review before twin creation.

**Layout**:
- Section title: "Review Your Twin Configuration"
- Organized sections for each category
- Edit buttons to return to specific steps
- "Create My Twin" CTA button

**Component Structure**:
```typescript
function ReviewStep({ data, onComplete, onEdit }: StepProps) {
  const { questionnaire, selectedModel, cognitiveBlend } = data;
  const model = data.availableModels.find(m => m.id === selectedModel);
  const blendZone = getBlendZone(cognitiveBlend);

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Review Your Twin Configuration</h2>

      {/* Personality Summary */}
      <GlassPanel className="p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Personality Profile</h3>
          <button onClick={() => onEdit(2)} className="text-purple-700 text-sm">
            Edit
          </button>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-neutral-600">Communication Style</p>
            <p className="font-medium">
              Formality: {Math.round(questionnaire.communication_style.formality * 100)}%
            </p>
            <p className="font-medium">
              Warmth: {Math.round(questionnaire.communication_style.warmth * 100)}%
            </p>
          </div>
          <div>
            <p className="text-sm text-neutral-600">Decision Making</p>
            <p className="font-medium">
              Risk Tolerance: {Math.round(questionnaire.decision_patterns.risk_tolerance * 100)}%
            </p>
          </div>
        </div>
      </GlassPanel>

      {/* AI Model */}
      <GlassPanel className="p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">AI Model</h3>
          <button onClick={() => onEdit(5)} className="text-purple-700 text-sm">
            Edit
          </button>
        </div>
        
        <div className="flex items-center gap-4">
          <Sparkles className="w-8 h-8 text-purple-700" />
          <div>
            <p className="font-semibold">{model?.name}</p>
            <p className="text-sm text-neutral-600">{model?.description}</p>
          </div>
        </div>
      </GlassPanel>

      {/* Cognitive Blend */}
      <GlassPanel className="p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Cognitive Blend</h3>
          <button onClick={() => onEdit(6)} className="text-purple-700 text-sm">
            Edit
          </button>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-purple-700">
            {cognitiveBlend}%
          </div>
          <div>
            <p className="font-semibold">{blendZone?.label}</p>
            <p className="text-sm text-neutral-600">{blendZone?.description}</p>
          </div>
        </div>
      </GlassPanel>

      <button
        onClick={() => onComplete()}
        className="w-full py-4 bg-purple-700 text-white text-lg font-semibold rounded-lg hover:bg-purple-600"
      >
        Create My Twin
      </button>
    </div>
  );
}
```



### Step 9: Creating Twin (Loading State)

**Purpose**: Provide feedback while twin is being created on backend.

**Layout**:
- Centered loading animation
- Status text
- Progress indicator (optional)
- No navigation buttons (user must wait)

**Component Structure**:
```typescript
function CreatingStep({ data, onComplete }: StepProps) {
  const [status, setStatus] = useState('Initializing...');

  useEffect(() => {
    const createTwin = async () => {
      try {
        setStatus('Creating your cognitive profile...');
        
        // Call twin creation API
        const twin = await onboardingApi.complete({
          responses: data.questionnaire,
          model: data.selectedModel,
          cognitive_blend: data.cognitiveBlend,
        });
        
        setStatus('Twin created successfully!');
        
        // Wait a moment before transitioning
        setTimeout(() => {
          onComplete({ twinId: twin.id });
        }, 1000);
        
      } catch (error) {
        setStatus('Error creating twin');
        // Handle error - show retry option
      }
    };

    createTwin();
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <div className="relative">
        <div className="w-24 h-24 border-4 border-purple-200 border-t-purple-700 rounded-full animate-spin" />
        <Sparkles className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-12 h-12 text-purple-700" />
      </div>
      
      <p className="mt-8 text-xl font-semibold text-neutral-800">
        {status}
      </p>
      
      <p className="mt-2 text-sm text-neutral-600">
        This may take a few moments...
      </p>
    </div>
  );
}
```

**Backend Processing**:
1. Validate all questionnaire responses
2. Create CSM profile from questionnaire data
3. Create Twin record with selected model and blend
4. Link Twin to CSM profile
5. Initialize default permissions
6. Return Twin ID and configuration



### Step 10: Success Screen

**Purpose**: Celebrate twin creation and guide user to next steps.

**Layout**:
- Success icon/animation
- Congratulatory message
- Brief explanation of what happens next
- "Go to Dashboard" CTA button
- Optional: Quick tips or tutorial link

**Component Structure**:
```typescript
function SuccessStep({ data }: StepProps) {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-[500px] text-center">
      <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mb-6">
        <CheckCircle className="w-16 h-16 text-green-600" />
      </div>
      
      <h2 className="text-3xl font-bold text-neutral-800 mb-4">
        Your Twin is Ready!
      </h2>
      
      <p className="text-lg text-neutral-700 max-w-md mb-8">
        Your cognitive digital twin has been created and is ready to learn from you. 
        Head to your dashboard to start connecting apps and teaching your Twin.
      </p>

      <GlassPanel className="p-6 max-w-md mb-8">
        <h3 className="font-semibold mb-3">Next Steps</h3>
        <ul className="text-left space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-purple-700 font-bold">1.</span>
            <span>Connect your first app (WhatsApp, Gmail, etc.)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-700 font-bold">2.</span>
            <span>Review and adjust your Twin's permissions</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-700 font-bold">3.</span>
            <span>Start a conversation to help your Twin learn</span>
          </li>
        </ul>
      </GlassPanel>

      <button
        onClick={() => router.push('/dashboard/twin')}
        className="px-8 py-4 bg-purple-700 text-white text-lg font-semibold rounded-lg hover:bg-purple-600"
      >
        Go to Dashboard
      </button>
    </div>
  );
}
```

## Error Handling

### Error Types and Recovery

```typescript
enum OnboardingErrorType {
  NETWORK_ERROR = 'network_error',
  VALIDATION_ERROR = 'validation_error',
  API_ERROR = 'api_error',
  SESSION_EXPIRED = 'session_expired',
  PAYMENT_ERROR = 'payment_error',
}

interface OnboardingError {
  type: OnboardingErrorType;
  message: string;
  details?: Record<string, any>;
  recoverable: boolean;
}

function handleError(error: OnboardingError): void {
  switch (error.type) {
    case OnboardingErrorType.NETWORK_ERROR:
      // Show retry button
      showErrorToast('Connection lost. Please check your internet and try again.');
      break;
      
    case OnboardingErrorType.VALIDATION_ERROR:
      // Highlight invalid fields
      showFieldErrors(error.details);
      break;
      
    case OnboardingErrorType.SESSION_EXPIRED:
      // Redirect to login with return URL
      router.push(`/auth/login?returnUrl=/onboarding?step=${currentStep}`);
      break;
      
    case OnboardingErrorType.PAYMENT_ERROR:
      // Show payment-specific error
      showErrorToast(error.message);
      break;
      
    case OnboardingErrorType.API_ERROR:
      // Show generic error with support contact
      showErrorToast('Something went wrong. Please contact support if this persists.');
      break;
  }
}
```

### Progress Recovery

```typescript
// On component mount, check for saved progress
useEffect(() => {
  const loadProgress = async () => {
    try {
      const response = await onboardingApi.start();
      
      if (response.saved_responses) {
        // Resume from saved progress
        setState({
          questionnaire: response.saved_responses,
          selectedModel: response.selected_model,
          cognitiveBlend: response.selected_blend || 50,
          currentStep: calculateResumeStep(response),
        });
        
        showInfoToast('Resuming from where you left off');
      }
    } catch (error) {
      handleError(error);
    }
  };
  
  loadProgress();
}, []);

function calculateResumeStep(data: OnboardingStartResponse): number {
  // Determine which step to resume from based on saved data
  if (!data.saved_responses) return 1;
  if (!data.saved_responses.communication_style) return 2;
  if (!data.saved_responses.decision_patterns) return 3;
  if (!data.saved_responses.preferences) return 4;
  if (!data.selected_model) return 5;
  if (!data.selected_blend) return 6;
  return 8; // Go to review
}
```



## Testing Strategy

### Testing Approach

The Twin Onboarding Frontend will use a dual testing approach combining unit tests for specific behaviors and property-based tests for universal correctness properties. This ensures both concrete edge cases and general correctness are validated.

### Unit Testing

Unit tests will focus on:
- **Component rendering**: Verify each step component renders correctly with various props
- **Validation logic**: Test field validation functions with specific valid/invalid inputs
- **Navigation flow**: Test step transitions and back button behavior
- **Error handling**: Test specific error scenarios and recovery mechanisms
- **API integration**: Mock API calls and test response handling

**Testing Framework**: Jest + React Testing Library

**Example Unit Tests**:
```typescript
describe('SliderQuestion', () => {
  it('should render with initial value', () => {
    render(<SliderQuestion value={0.5} onChange={jest.fn()} />);
    expect(screen.getByRole('slider')).toHaveValue('0.5');
  });

  it('should call onChange when slider moves', () => {
    const onChange = jest.fn();
    render(<SliderQuestion value={0.5} onChange={onChange} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0.7' } });
    expect(onChange).toHaveBeenCalledWith(0.7);
  });
});

describe('validateCommunicationStyle', () => {
  it('should return false when required fields missing', () => {
    const state = { questionnaire: { communication_style: {} } };
    expect(validateCommunicationStyle(state)).toBe(false);
  });

  it('should return true when all required fields present', () => {
    const state = {
      questionnaire: {
        communication_style: {
          openness: 0.7,
          extraversion: 0.6,
          agreeableness: 0.8,
          formality: 0.4,
          warmth: 0.7,
          directness: 0.6,
          preferred_greeting: 'Hey',
          sign_off_style: 'Cheers',
        }
      }
    };
    expect(validateCommunicationStyle(state)).toBe(true);
  });
});
```

### Property-Based Testing

Property tests will validate universal behaviors across many generated inputs. Each property test will run a minimum of 100 iterations with randomized data.

**Testing Framework**: fast-check (JavaScript property-based testing library)

**Property Test Configuration**:
- Minimum 100 iterations per test
- Each test tagged with feature name and property number
- Tests reference design document properties

### Integration Testing

Integration tests will verify:
- Complete wizard flow from start to finish
- API integration with backend endpoints
- State persistence and recovery
- Payment flow integration
- Redirect logic after twin creation

### Accessibility Testing

Accessibility tests will ensure:
- Keyboard navigation works for all interactive elements
- Screen reader compatibility (ARIA labels)
- Color contrast meets WCAG AA standards
- Touch targets meet minimum size requirements (44px)

**Testing Tools**: jest-axe for automated accessibility testing



## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:
- Navigation properties (2.2, 2.3) can be combined into a single property about button visibility
- Question rendering properties (4.4-4.7) can be combined into a single property about type-appropriate controls
- Model display properties (5.2, 5.3) can be combined into a single property about tier-based indicators
- Error handling properties (12.1, 12.2, 12.5) share common error display behavior

### Core Properties

**Property 1: Query Parameter Preservation During Redirects**
*For any* redirect operation in the onboarding wizard, all query parameters present in the current URL should be preserved in the destination URL.
**Validates: Requirements 1.3**

**Property 2: Progress Indicator Accuracy**
*For any* step number between 1 and total steps, the progress indicator should display the correct current step, total steps, and percentage complete.
**Validates: Requirements 2.1**

**Property 3: Navigation Button Visibility**
*For any* step number N in the wizard, the Back button should be visible if and only if N > 1, and the Next button should be visible if and only if N < total steps.
**Validates: Requirements 2.2, 2.3**

**Property 4: Data Preservation During Back Navigation**
*For any* form data entered in a step, navigating back and then forward should preserve all entered values without loss.
**Validates: Requirements 2.4**

**Property 5: Validation Prevents Invalid Advancement**
*For any* step with required fields, attempting to advance with incomplete data should display validation errors and prevent navigation to the next step.
**Validates: Requirements 2.5, 4.8**

**Property 6: Keyboard Navigation Support**
*For any* step in the wizard, pressing Enter should advance to the next step (if valid), and pressing Escape should navigate to the previous step (if not on first step).
**Validates: Requirements 2.6**

**Property 7: Question Type Determines Input Control**
*For any* question in the questionnaire, the rendered input control should match the question type (slider for "slider", text input for "text", select cards for "select", multi-input for "text_list").
**Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.7**

**Property 8: Model Tier Availability Indicators**
*For any* AI model and user subscription tier, the model card should display an "available" state if the user's tier meets or exceeds the model's required tier, otherwise display an "upgrade required" state.
**Validates: Requirements 5.2, 5.3, 5.4**

**Property 9: Cognitive Blend Description Updates**
*For any* cognitive blend value between 0-100, adjusting the slider should immediately update the displayed zone description to match the value's range (0-30: Pure AI Logic, 31-70: Balanced, 71-100: Heavy Personality).
**Validates: Requirements 6.3**

**Property 10: Payment Form Validation**
*For any* card details input, submitting with invalid data (empty fields, invalid format) should display field-specific validation errors and prevent API submission.
**Validates: Requirements 7.3**

**Property 11: Progress Saving After Step Completion**
*For any* completed step in the wizard, the system should call the progress API with the current state before advancing to the next step.
**Validates: Requirements 8.1**

**Property 12: Saved Progress Restoration**
*For any* saved progress data, loading the onboarding wizard should pre-populate all form fields with the saved values and navigate to the appropriate resume step.
**Validates: Requirements 8.3, 8.4**

**Property 13: Review Screen Data Organization**
*For any* completed questionnaire, the review screen should display all answers grouped by their respective sections (Communication Style, Decision Making, Preferences).
**Validates: Requirements 9.2**

**Property 14: Edit Links Navigate to Correct Steps**
*For any* edit link on the review screen, clicking it should navigate to the specific step where that data was collected.
**Validates: Requirements 9.5**

**Property 15: Twin Creation API Call Completeness**
*For any* twin creation request, the API call should include all required fields: complete questionnaire responses (all three sections), selected model, and cognitive blend value.
**Validates: Requirements 10.1**

**Property 16: Touch Target Minimum Size**
*For any* interactive element (button, link, input) in the wizard, the touch target size should be at least 44px × 44px on mobile devices.
**Validates: Requirements 11.4**

**Property 17: Keyboard Accessibility**
*For any* interactive element in the wizard, it should be reachable and operable using only keyboard navigation (Tab, Enter, Escape, Arrow keys).
**Validates: Requirements 11.5**

**Property 18: ARIA Label Presence**
*For any* interactive element without visible text (icons, sliders, custom controls), an appropriate ARIA label should be present for screen readers.
**Validates: Requirements 11.6**

**Property 19: Color Contrast Compliance**
*For any* text element in the wizard, the color contrast ratio between text and background should meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text).
**Validates: Requirements 11.7**

**Property 20: Error Message Display**
*For any* API error or validation failure, the system should display a user-friendly error message that explains the problem and provides actionable next steps.
**Validates: Requirements 12.1, 12.3, 12.5**

**Property 21: Network Error Recovery**
*For any* network error during API calls, the system should display a retry button that allows the user to reattempt the failed operation.
**Validates: Requirements 12.2**

