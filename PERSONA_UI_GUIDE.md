# Persona/Submodels UI - Visual Guide

## 🎨 What I Built

A complete persona management system that integrates with your existing model manager. Here's the full flow:

---

## 📱 Screen Flow

### **Screen 1: Model Manager (Existing - Updated)**
```
┌─────────────────────────────────────────────────────────────┐
│  Model Manager                    [+ Create Model]          │
│  Manage your AI models and personas                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ [Image]  │  │ [Image]  │  │ [Image]  │                 │
│  │ Skyler   │  │ Emily    │  │ Sara     │                 │
│  │ Trained  │  │ Training │  │ Not      │                 │
│  │          │  │          │  │ Started  │                 │
│  │ 👤 3     │  │ 👤 1     │  │ 👤 0     │                 │
│  │ 📷 247   │  │ 📷 12    │  │ 📷 0     │                 │
│  │ ✅ 156   │  │ ✅ 3     │  │ ✅ 0     │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│                                                              │
│  Click any model card to manage its personas →              │
└─────────────────────────────────────────────────────────────┘
```

---

### **Screen 2: Persona Manager (NEW!)**
When you click a model, you see this:

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Models                                           │
├─────────────────────────────────────────────────────────────┤
│  ┌────────┐  Skyler Mae                                     │
│  │ Model  │  Professional Instagram influencer              │
│  │ Image  │  🏷️ skyler                                      │
│  └────────┘  📷 @skyler_official                            │
│                                      [+ Create Persona]     │
├─────────────────────────────────────────────────────────────┤
│  Personas (3)                                                │
│  Each persona uses the base Skyler model with different     │
│  target face and identity                                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ [Face Img]   │  │ [Face Img]   │  │ [Face Img]   │     │
│  │ 🟣 Gaming    │  │ 🟣 Fitness   │  │ 🟣 Fashion   │     │
│  │              │  │              │  │              │     │
│  │ SkylerGamer  │  │ SkylerFit    │  │ SkylerStyle  │     │
│  │ Face: Edgy   │  │ Face: Athlet │  │ Face: Elegant│     │
│  │              │  │              │  │              │     │
│  │ 📷 @s_gamer  │  │ 📷 @s_fitness│  │ 📷 @s_fashion│     │
│  │              │  │              │  │              │     │
│  │ 💙 89        │  │ 💙 124       │  │ 💙 34        │     │
│  │ ✅ 52        │  │ ✅ 87        │  │ ✅ 17        │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  Click any persona card to view details →                   │
└─────────────────────────────────────────────────────────────┘
```

---

### **Screen 3: Create Persona Modal (NEW!)**
When you click "+ Create Persona":

```
┌────────────────────────────────────────────────────────────────┐
│  Create New Persona                                      [X]   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌────────────────────────────────┐ │
│  │ TARGET FACE IMAGE   │  │ PERSONA DETAILS                │ │
│  │                     │  │                                │ │
│  │ ┌─────────────────┐ │  │ Persona Name *                 │ │
│  │ │  [Upload Area]  │ │  │ ┌───────────────────────────┐ │ │
│  │ │  📤 Click to    │ │  │ │ SkylerGamerGirl           │ │ │
│  │ │  upload target  │ │  │ └───────────────────────────┘ │ │
│  │ │  face           │ │  │                                │ │
│  │ │                 │ │  │ Niche                          │ │
│  │ │  This face will │ │  │ ┌───────────────────────────┐ │ │
│  │ │  be swapped onto│ │  │ │ [Gaming ▼]                │ │ │
│  │ │  generated imgs │ │  │ └───────────────────────────┘ │ │
│  │ └─────────────────┘ │  │                                │ │
│  │                     │  │ Reference Library              │ │
│  │ Target Face Name    │  │ ┌───────────────────────────┐ │ │
│  │ ┌─────────────────┐ │  │ │ Gaming Poses (147 imgs) ▼ │ │ │
│  │ │ Edgy Gamer Face │ │  │ └───────────────────────────┘ │ │
│  │ └─────────────────┘ │  │ Optional: reference poses      │ │
│  │                     │  │                                │ │
│  └─────────────────────┘  │ Description                    │ │
│                            │ ┌───────────────────────────┐ │ │
│                            │ │ Gaming influencer with... │ │ │
│                            │ └───────────────────────────┘ │ │
│                            │                                │ │
│                            │ Default Prompt Prefix          │ │
│                            │ ┌───────────────────────────┐ │ │
│                            │ │ gaming setup, RGB lights, │ │ │
│                            │ └───────────────────────────┘ │ │
│                            │                                │ │
│                            │ Default Strength: 0.75         │ │
│                            │ ├─────●─────────────────────┤ │ │
│                            │                                │ │
│                            └────────────────────────────────┘ │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  SOCIAL MEDIA ACCOUNTS                                         │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │
│  │ 📷 Instagram  │  │ 🎵 TikTok     │  │ OnlyFans      │    │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │    │
│  │ │ s_gamer   │ │  │ │ s_gamer   │ │  │ │ s_gamer   │ │    │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │    │
│  └───────────────┘  └───────────────┘  └───────────────┘    │
│  These accounts will be used for posting generated content     │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│                [Cancel]  [✨ Create Persona]                   │
└────────────────────────────────────────────────────────────────┘
```

---

### **Screen 4: Persona Detail Modal (NEW!)**
When you click a persona card:

```
┌────────────────────────────────────────────────────────────────┐
│  SkylerGamerGirl                                         [X]   │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  SkylerGamerGirl                                 │
│  │          │  🟣 Gaming                                        │
│  │  Target  │                                                   │
│  │  Face    │  Target Face: Edgy Gamer Face                    │
│  │  Image   │  Gaming influencer with edgy personality         │
│  │          │                                                   │
│  │  [Photo] │  📷 @skyler_gamer  🎵 @s_gamer                   │
│  │          │                                                   │
│  └──────────┘  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│                 │ 💙 89  │ │ ✅ 52  │ │ 0.75   │ │   ✅   │   │
│                 │Generated│ │ Posted │ │Strength│ │Connect │   │
│                 └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Default Prompt Prefix                                         │
│  gaming setup, RGB lighting, headset,                          │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│  [✨ Generate Content]  [🖼️ View Gallery]  [Close]            │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### **1. Model → Persona Hierarchy**
- One model (base LoRA) can have multiple personas
- Each persona = different target face + different identity
- Stats roll up: Model shows total across all personas

### **2. Target Face Upload**
- **CRITICAL**: Each persona requires a target face image
- This is the face that gets swapped onto generated content
- Preview before creating persona

### **3. Niche System**
- Personas are organized by niche (Gaming, Fitness, Yoga, etc.)
- Reference libraries are filtered by niche
- Helps organize content strategy

### **4. Reference Libraries**
- Optional: Link persona to reference library for poses
- Libraries contain reference images scraped from Instagram
- Reusable across personas in same niche

### **5. Generation Settings**
- Default prompt prefix: Added to all generations
- Default strength: How much to use reference image (if library selected)
- Can be overridden per generation

### **6. Social Media Integration**
- Each persona has its own social accounts
- Instagram, TikTok, OnlyFans usernames
- Used for posting generated content

### **7. Stats Tracking**
- Total generated: Number of images created
- Total posted: Number of images posted to social media
- Displayed on both model and persona cards

---

## 🎨 Design Highlights

### **Colors:**
- Blue/Purple gradient for primary actions
- Purple badges for niche tags
- Pink for Instagram references
- Slate/dark theme throughout

### **Interactive Elements:**
- Hover effects on all cards
- Smooth transitions
- Loading states with spinners
- Form validation (required fields)

### **Layout:**
- Grid layout for cards (responsive)
- Two-column modal for create persona
- Clean header with back navigation
- Stats displayed prominently

---

## 🔄 User Flow Example

1. **User clicks "Skyler Mae" model card**
   → Opens Persona Manager screen

2. **User clicks "+ Create Persona"**
   → Opens create modal

3. **User fills in:**
   - Uploads target face image (edgy gamer face)
   - Names persona "SkylerGamerGirl"
   - Selects "Gaming" niche
   - Selects "Gaming Poses" reference library
   - Sets Instagram to @skyler_gamer
   - Sets default prompt prefix: "gaming setup, RGB lighting,"

4. **User clicks "Create Persona"**
   → Persona created and appears in grid

5. **User clicks persona card**
   → Opens detail view

6. **User clicks "Generate Content"**
   → (This will trigger generation workflow - to be built)

---

## 📊 Database Integration

### **What Gets Saved:**
- Persona name, description, niche
- Target face URL (uploaded to Supabase storage)
- Reference library ID (optional link)
- Social media usernames
- Default generation settings
- Stats (auto-updated via triggers)

### **API Endpoints Needed:**
```
POST /api/persona/personas
- Create new persona with target face upload

GET /api/persona/models/{id}/personas
- List personas for a model

GET /api/persona/personas/{id}
- Get persona details

PUT /api/persona/personas/{id}
- Update persona settings

GET /api/persona/reference-libraries
- List available reference libraries (filtered by niche)
```

---

## ✅ What's Ready

✅ Full UI components built
✅ Form validation
✅ File upload preview
✅ Navigation between screens
✅ Responsive layout
✅ Loading states
✅ Empty states

## ⏳ What's Next (API Implementation)

❌ Backend endpoints for persona CRUD
❌ Target face image upload to Supabase storage
❌ Reference library API endpoints
❌ Integration with generation workflow

---

**The UI is 100% ready. You can now see the full vision of the persona system!** 🎉

Let me know if you want me to implement the backend API next, or adjust anything in the UI design.
