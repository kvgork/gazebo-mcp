# Live Demo Scripts

Professional scripts for delivering live demonstrations at conferences, workshops, and presentations.

## Available Scripts

### 1. **5-Minute Lightning Talk** (`01_lightning_talk/`)
**Format**: Conference lightning talk
**Audience**: 50-500 people, mixed technical levels
**Goal**: Quick wow moment, generate interest

**Content**:
- 1 min: Hook (show robot moving immediately)
- 2 min: Core capability demonstration
- 1 min: "How it works" brief explanation
- 1 min: Call to action (QR code, links)

**Preparation**: 5 minutes
**Reliability**: Very high (minimal live interaction)

---

### 2. **15-Minute Technical Deep-Dive** (`02_technical_deepdive/`)
**Format**: Technical breakout session
**Audience**: 20-100 developers/researchers
**Goal**: Show technical capabilities and architecture

**Content**:
- 3 min: Problem statement and motivation
- 5 min: Live demonstration (2 scenarios)
- 4 min: Architecture explanation
- 3 min: Q&A

**Preparation**: 15 minutes
**Reliability**: High (with backup plans)

---

### 3. **30-Minute Conference Presentation** (`03_conference_presentation/`)
**Format**: Full conference talk slot
**Audience**: 50-200 technical attendees
**Goal**: Comprehensive overview with deep technical insights

**Content**:
- 5 min: Introduction and context
- 12 min: Live demonstrations (3-4 scenarios)
- 8 min: Technical deep-dive
- 5 min: Q&A

**Preparation**: 30 minutes
**Reliability**: Medium-high (longer = more risk)

---

### 4. **1-Hour Hands-On Workshop** (`04_workshop/`)
**Format**: Interactive workshop
**Audience**: 10-30 participants with laptops
**Goal**: Participants build and run examples themselves

**Content**:
- 10 min: Introduction and setup verification
- 20 min: Guided exercises (3-4 examples)
- 20 min: Free exploration with assistance
- 10 min: Wrap-up and next steps

**Preparation**: 60 minutes + setup testing
**Reliability**: Variable (depends on participant setup)

---

### 5. **2-Hour Masterclass** (`05_masterclass/`)
**Format**: In-depth training session
**Audience**: 5-20 advanced users
**Goal**: Deep understanding and advanced techniques

**Content**:
- 20 min: Foundations and setup
- 40 min: Core concepts with demonstrations
- 40 min: Advanced topics and custom development
- 20 min: Q&A and individual assistance

**Preparation**: 90 minutes
**Reliability**: Medium (interactive, advanced content)

---

### 6. **4-Hour Bootcamp** (`06_bootcamp/`)
**Format**: Half-day intensive training
**Audience**: 10-20 committed learners
**Goal**: Complete skill development from zero to competent

**Content**:
- Hour 1: Setup and basics
- Hour 2: Intermediate concepts
- Hour 3: Advanced topics
- Hour 4: Project work and troubleshooting

**Preparation**: 2 hours + materials
**Reliability**: High (time for recovery and adaptation)

---

## Quick Selection Guide

**Choose by time available**:
- 5 min → Lightning Talk
- 15 min → Technical Deep-Dive
- 30 min → Conference Presentation
- 60 min → Workshop
- 120 min → Masterclass
- 240 min → Bootcamp

**Choose by audience**:
- **Executives/Non-technical** → Lightning Talk or Conference Presentation
- **Developers** → Technical Deep-Dive or Workshop
- **Researchers** → Conference Presentation or Masterclass
- **Students** → Workshop or Bootcamp

**Choose by goal**:
- **Marketing/Awareness** → Lightning Talk
- **Technical Validation** → Technical Deep-Dive
- **Education** → Workshop or Bootcamp
- **Community Building** → Masterclass
- **Comprehensive Training** → Bootcamp

---

## File Structure

Each script directory contains:

```
live_demos/XX_script_name/
├── SCRIPT.md              # Complete presentation script
├── SLIDES.md              # Slide outline (create in your tool)
├── TIMING_GUIDE.md        # Detailed timing breakdown
├── SETUP_CHECKLIST.md     # Pre-presentation checklist
├── RECOVERY_PLAN.md       # What to do if things fail
├── HANDOUTS.md            # Materials to give attendees
└── assets/
    ├── qr_codes/          # QR codes for links
    ├── demos/             # Demo recordings (backup)
    └── examples/          # Code examples to share
```

---

## General Best Practices

### Before Presentation

**1 Week Before**:
- [ ] Reserve presentation room/slot
- [ ] Test internet connection requirements
- [ ] Prepare backup materials (videos, slides)
- [ ] Create handouts and QR codes

**1 Day Before**:
- [ ] Test full setup on presentation hardware
- [ ] Record backup videos of all demos
- [ ] Print emergency recovery guide
- [ ] Prepare participant materials (if workshop)

**1 Hour Before**:
- [ ] Arrive early to set up
- [ ] Test A/V equipment
- [ ] Launch all required software
- [ ] Run through quick test demo

**15 Minutes Before**:
- [ ] Attendees arriving - greet and chat
- [ ] Final system check
- [ ] Have backup plan ready
- [ ] Take deep breath - you've got this!

### During Presentation

**Do**:
- ✅ Start with a hook (show, don't tell)
- ✅ Make eye contact with audience
- ✅ Speak slower than you think necessary
- ✅ Pause after important points
- ✅ Interact with audience (questions, polls)
- ✅ Have fun and show enthusiasm!

**Don't**:
- ❌ Apologize for technical difficulties excessively
- ❌ Read slides word-for-word
- ❌ Turn your back to audience for long
- ❌ Rush through content
- ❌ Ignore audience questions
- ❌ Give up if demo fails (use backup!)

### After Presentation

**Immediately**:
- Answer questions
- Share materials (QR codes, links)
- Collect feedback
- Network with interested attendees

**Within 24 Hours**:
- Send follow-up email with resources
- Post demo video/recording
- Share slides/materials publicly
- Thank organizers

**Within 1 Week**:
- Review what worked and what didn't
- Update scripts based on feedback
- Respond to email questions
- Share on social media

---

## Emergency Recovery

### Demo Fails Completely

**Option 1**: Pre-recorded backup
```
"Let me show you the recording from our test run this morning..."
[Play backup video, narrate over it]
```

**Option 2**: Slide-based explanation
```
"While the live demo is having issues, let me walk you through what you would see..."
[Use slides with screenshots]
```

**Option 3**: Offer offline demo
```
"I'll stay after to demonstrate one-on-one for anyone interested."
[Continue with slides, make good on promise]
```

### Internet Fails

**Prevention**: Download everything needed locally
```bash
# Before presentation
./download_all_assets.sh  # Downloads models, resources
./test_offline_mode.sh    # Verifies works without internet
```

**Recovery**: Use local resources only
```
"Good news - everything runs locally, so we're fine!"
[Continue with offline-capable demos]
```

### Time Running Short

**5 min over**: Skip one demo section
**10 min over**: Skip to closing slides
**15+ min over**: Ask organizers for extension or offer to continue offline

---

## Customization Guide

### Adapting to Your Audience

**For Non-Technical Audiences**:
- Use more analogies and less jargon
- Show outcomes, not process
- Focus on "what" and "why", less on "how"
- Use impressive visuals

**For Technical Audiences**:
- Show code and architecture
- Explain implementation details
- Discuss trade-offs and alternatives
- Welcome technical questions

**For Research Audiences**:
- Emphasize reproducibility
- Discuss metrics and benchmarking
- Compare to related work
- Highlight novel contributions

### Adjusting Timing

**Running Long**:
- Skip less critical demos
- Reduce Q&A time
- Speak slightly faster (but stay clear)
- Skip backup explanations

**Running Short**:
- Add interactive element
- Extended Q&A
- Live audience suggestions
- Deeper technical explanation

---

## Presentation Tips by Format

### Lightning Talks
- **Hook immediately** - start with action
- **One key message** - what should they remember?
- **Strong close** - clear call to action
- **Practice timing** - 5 minutes is SHORT

### Technical Deep-Dives
- **Assume knowledge** - don't explain basics
- **Show complexity** - they want to see under the hood
- **Invite questions** - encourage interaction
- **Provide resources** - links to docs, code

### Workshops
- **Verify setup** - everyone ready before starting
- **Go slow** - let people follow along
- **Check understanding** - ask "everyone got this?"
- **Assist individuals** - have helpers if possible

### Masterclasses
- **Interactive** - more discussion, less lecture
- **Advanced content** - push boundaries
- **Small group** - leverage intimacy
- **Flexible** - adapt to participant interests

---

## Audience Engagement

### Techniques

**Polls**:
```
"Quick poll - who here has used ROS2 before?"
[Show of hands, adjust technical level accordingly]
```

**Questions**:
```
"What would you want a robot to do in this scenario?"
[Take suggestions, incorporate if possible]
```

**Challenges**:
```
"I'll give a prize to whoever can suggest the most creative command!"
[Builds excitement and interaction]
```

**Callbacks**:
```
Reference earlier audience comments:
"As Sarah asked earlier about multi-robot..."
[Makes audience feel heard]
```

### Handling Questions

**During Presentation**:
- Brief questions: Answer immediately
- Complex questions: "Great question - let's discuss after" (and DO discuss after)
- Off-topic: "Interesting - can we chat after?"

**After Presentation**:
- Stand where approached easily
- Give full attention to each person
- Offer to exchange contact info
- Follow up on promises

---

## Technical Setup

### Required Equipment

**Minimum**:
- Laptop with ROS2 + Gazebo + MCP installed
- HDMI/display adapter
- Power supply
- Backup: USB with videos and slides

**Recommended**:
- Second laptop (backup)
- Wireless presenter/clicker
- Backup internet (phone hotspot)
- Printed recovery guide
- Water bottle

**Optional**:
- Microphone (for large rooms)
- Document camera (for hardware demos)
- Tablet for notes
- Voice recorder for review

### Software Checklist

Pre-launch:
- [ ] ROS2 sourced
- [ ] Gazebo tested
- [ ] MCP server running
- [ ] Claude Code connected
- [ ] Demo robots spawned (if applicable)
- [ ] Backup videos ready
- [ ] Slides open
- [ ] Email/notifications off
- [ ] Screen mirroring working

---

## Materials to Share

**Always Provide**:
- GitHub repository link
- Documentation URL
- Contact information
- Tutorial starting point

**Nice to Have**:
- QR code for quick access
- Printed quick-reference card
- USB with examples
- Certificate of attendance (workshops)

**Follow-Up**:
- Email with all links
- Recording (if permitted)
- Slides (PDF)
- Example code repositories

---

## Success Metrics

Track these to improve:

**Attendance**:
- How many attended?
- Stayed for full duration?
- Asked questions?

**Engagement**:
- Questions asked: ___
- Hands-on participation: ___
- Social media mentions: ___

**Technical**:
- Demos that worked: ___/___
- Recovery plans used: ___
- Setup time: ___

**Follow-Up**:
- Emails received: ___
- GitHub stars/forks: ___
- Tutorial completions: ___

**Feedback**:
- Average rating: ___/5
- Would recommend: ___%
- Most liked: ___
- Needs improvement: ___

---

## Resources

**Presentation Skills**:
- "Presentation Zen" by Garr Reynolds
- "Talk Like TED" by Carmine Gallo
- YouTube: Search "technical presentation tips"

**Demo Techniques**:
- SIGGRAPH presentation guidelines
- ROS World talk examples
- Apple keynote breakdowns

**Tools**:
- **Slides**: reveal.js, PowerPoint, Keynote, Google Slides
- **Screen Recording**: OBS Studio, SimpleScreenRecorder
- **QR Codes**: qrencode, online generators
- **Timing**: Presentation timers, phone stopwatch

---

**Remember**: The best presentations come from practice. Rehearse each script 3+ times before delivering live. You've got this! 🎤🚀
