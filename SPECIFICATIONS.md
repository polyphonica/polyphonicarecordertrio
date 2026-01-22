# Polyphonica Recorder Trio - Website Specifications

## Overview
A professional website for Polyphonica Recorder Trio featuring concert and workshop listings with booking/payment capabilities.

**Domain**: https://www.polyphonicarecordertrio.com/

## Tech Stack
- **Framework**: Django
- **Database**: SQLite (local development), PostgreSQL (production on IONOS)
- **Payments**: Stripe
- **Email**: Django email (for booking confirmations)
- **CSS**: TBD (considering Tailwind CSS for professional, custom look)

## Pages & Navigation

### Menu Bar
`Home | About | Concerts | Workshops | Media | Contact`

(No separate gallery page - Media page covers audio/video/photos)

### 1. Home Page
- Featured hero image/photo of the trio
- Introductory blurb about the trio
- Upcoming concerts/workshops highlights (optional)
- Professional, elegant design

### 2. About Page
- General trio information and history
- Individual player biographies (3 members):
  - Grace Barton
  - Simone Reid
  - Michael Piraner
- Each bio includes: photo, text, optional links
- Biographies managed via admin forms (stored in database)

### 3. Concerts Page
- List of upcoming concerts
- Each concert displays:
  - Title, date, time, venue
  - Description
  - Ticket pricing (full price + discount categories)
  - Either: "Buy Tickets" (Stripe checkout) OR external ticket URL
- Past concerts archive (optional)

### 4. Workshops Page
- List of upcoming workshops
- Each workshop displays:
  - Title, date, time
  - Delivery method: Online / In-Person / Hybrid
  - Venue details (for in-person)
  - Description, requirements
  - Price
  - Registration via Stripe checkout
- Capacity limits and registration tracking

### 5. Media Page
- Audio samples (embedded player or links)
- Video embeds (YouTube/Vimeo)
- Organized by category or performance

### 6. Contact Page
- Contact form (sends email to trio)
- General contact information
- Facebook link

## Admin Functionality
- Secure admin login (username/password)
- Admin can:
  - Create/edit/delete concerts
  - Create/edit/delete workshops
  - Create/edit/delete player biographies
  - Manage media content
  - View bookings/registrations

## Concert Model
- Title
- Date and time
- Venue (name, address, map link)
- Description
- Image
- Ticket pricing:
  - Full price
  - Discount price (seniors, students, disabled, etc.)
  - Discount label/description
- Ticket purchase method:
  - Internal (Stripe checkout via this site)
  - External (URL to third-party ticket seller)
- Capacity tracking (for internal sales):
  - Optional capacity limit (can be unlimited)
  - Current tickets sold count
  - Show "Sold Out" when limit reached
- Status (draft/published/past)

## Workshop Model (simplified from RECORDER-ED)
- Title
- Date and time
- Duration
- Delivery method (online/in-person/hybrid)
- Venue details (for in-person)
- Meeting link (for online)
- Description
- Prerequisites/requirements
- Price
- Capacity (max participants) - registration closes when full
- Current registrations count
- Status (draft/published/cancelled)
- **No series support** - single standalone workshops only
- **No waitlist** - simply show "Sold Out" when capacity reached

## User Accounts & Authentication

### Concerts
- **No account required** - guest checkout only
- Collect email for confirmation

### Workshops
- **Account required** for registration
- Needed for:
  - Downloading workshop documents/materials
  - Managing bookings
  - Terms & conditions acceptance
  - Cancellation and refund processing

## Booking & Payments
- Shopping cart functionality
- Stripe checkout integration
- Support for:
  - Concert tickets (guest checkout, with price type selection)
  - Workshop registrations (account required)
- **Email confirmations** sent automatically after booking
- Booking management in admin

## Workshop Terms & Conditions
- Terms must be accepted during registration
- Cancellation policy (same as RECORDER-ED):
  - Full refund only (no partial refunds)
  - Refund eligibility based on time before workshop
- Refund processing for eligible cancellations
- Terms stored and versioned (similar to RECORDER-ED)

## Workshop Materials
- Admin can upload documents for each workshop
- Registered participants can download materials
- Access controlled by registration status

## Social Media
- Facebook (primary)
- Others can be added later

## Future Considerations
- SEO optimization
- Google Analytics
- Additional social media platforms
- Newsletter/mailing list integration
