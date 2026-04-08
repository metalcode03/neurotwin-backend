# Phone Number Implementation

This document describes the phone number management feature added to NeuroTwin.

## Overview

Users can now manage their phone numbers with the following capabilities:
- Set a primary phone number
- Optionally set a separate WhatsApp number
- Toggle to use the primary number for WhatsApp (default behavior)

## Backend Changes

### Database Schema

Added three new fields to the `User` model:

```python
phone_number = models.CharField(max_length=20, blank=True, default='')
whatsapp_number = models.CharField(max_length=20, blank=True, default='')
use_default_for_whatsapp = models.BooleanField(default=True)
```

**Migration**: `apps/authentication/migrations/0006_add_phone_numbers.py`

### Model Methods

Added `effective_whatsapp_number` property to User model:
- Returns `phone_number` if `use_default_for_whatsapp` is True
- Returns `whatsapp_number` otherwise
- Useful for WhatsApp integration logic

### API Updates

**Serializers** (`apps/authentication/serializers.py`):
- Updated `UserProfileSerializer` to include phone number fields

**Views** (`apps/authentication/views.py`):
- Updated `CurrentUserView.get()` to return phone number fields
- `UserProfileView.put()` now accepts phone number updates

**Endpoints**:
- `GET /api/v1/auth/me` - Returns phone numbers
- `GET /api/v1/users/profile` - Returns phone numbers
- `PUT /api/v1/users/profile` - Updates phone numbers

## Frontend Changes

### Type Definitions

**AuthUser** (`neuro-frontend/src/types/auth.ts`):
```typescript
phoneNumber?: string;
whatsappNumber?: string;
useDefaultForWhatsapp?: boolean;
```

**UserProfile** (`neuro-frontend/src/types/user.ts`):
```typescript
phoneNumber?: string;
whatsappNumber?: string;
useDefaultForWhatsapp?: boolean;
```

**ProfileUpdateData** (`neuro-frontend/src/types/user.ts`):
```typescript
phoneNumber?: string;
whatsappNumber?: string;
useDefaultForWhatsapp?: boolean;
```

### API Client Updates

**Auth API** (`neuro-frontend/src/lib/api/auth.ts`):
- `getCurrentUser()` now maps phone number fields from backend

**User API** (`neuro-frontend/src/lib/api/user.ts`):
- `updateProfile()` now accepts and sends phone number fields

### UI Components

**PhoneNumberForm** (`neuro-frontend/src/components/profile/PhoneNumberForm.tsx`):
- New component for managing phone numbers
- Features:
  - Primary phone number input
  - WhatsApp number input (conditionally shown)
  - Toggle for using default number for WhatsApp
  - Form validation and error handling
  - Success/error notifications
  - Consistent with NeuroTwin design system

**Profile Settings Page** (`neuro-frontend/src/app/dashboard/settings/profile/page.tsx`):
- Added new "Phone Numbers" section
- Integrated PhoneNumberForm component
- Maintains consistent glass morphism design

## Design Consistency

The implementation follows NeuroTwin's design system:
- Glass morphism panels with `bg-white dark:bg-[#111113]`
- Purple accent colors (`purple-700`, `purple-600`)
- Consistent spacing and typography
- Smooth animations with Framer Motion
- Dark mode support
- Accessibility features (ARIA labels, semantic HTML)

## Usage

### For Users

1. Navigate to Settings → Profile
2. Scroll to "Phone Numbers" section
3. Enter primary phone number
4. Choose whether to use it for WhatsApp:
   - If enabled: Primary number used for WhatsApp
   - If disabled: Enter separate WhatsApp number

### For Developers

**Backend - Get effective WhatsApp number**:
```python
user = request.user
whatsapp_num = user.effective_whatsapp_number
```

**Frontend - Update phone numbers**:
```typescript
await userApi.updateProfile({
  phone_number: '+1234567890',
  use_default_for_whatsapp: true,
});
```

## Future Enhancements

- Phone number verification via SMS
- International format validation
- WhatsApp Business API integration
- Voice Twin phone number assignment
- Call history tracking

## Migration Instructions

To apply the database changes:

```bash
# Run migration
uv run python manage.py migrate authentication 0006_add_phone_numbers

# Or run all migrations
uv run python manage.py migrate
```

## Testing Checklist

- [ ] Backend migration runs successfully
- [ ] User can update primary phone number
- [ ] User can toggle WhatsApp preference
- [ ] User can set separate WhatsApp number
- [ ] `effective_whatsapp_number` returns correct value
- [ ] API endpoints return phone number fields
- [ ] Frontend form validates input
- [ ] Frontend displays success/error messages
- [ ] Dark mode styling works correctly
- [ ] Changes persist after page refresh
