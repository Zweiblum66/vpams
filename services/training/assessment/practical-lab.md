# MAMS Support Practical Assessment Lab

## Assessment Overview

This practical assessment evaluates your ability to handle real-world MAMS support scenarios. You will work in a live test environment with simulated issues.

**Duration**: 3 hours  
**Passing Score**: 80%  
**Environment**: MAMS Training Instance (https://training.mams.com)  
**Credentials**: Will be provided at start of assessment  

## Assessment Structure

1. **Basic Operations** (20%)
2. **Troubleshooting** (40%)
3. **Emergency Response** (25%)
4. **Documentation** (15%)

---

## Pre-Assessment Setup

### Environment Access
```bash
# SSH to training environment
ssh trainee@training.mams.com -p 2222

# Verify access to tools
docker ps
kubectl get pods
psql --version
redis-cli --version
```

### Available Resources
- Admin UI: https://training.mams.com/admin
- Grafana: https://training.mams.com/grafana
- Logs: /var/log/mams/
- Documentation: /home/trainee/docs/

---

## Part 1: Basic Operations (20 points)

### Task 1.1: User Management (5 points)
Create a new organization with the following requirements:
- Organization name: "Assessment Media Corp"
- Create 3 users with roles: Admin, Editor, Viewer
- Set storage quotas: Admin (500GB), Editor (200GB), Viewer (50GB)
- Enable MFA for Admin user

**Deliverables**:
- Screenshot of created users
- SQL query showing user details
- Test login for each user

### Task 1.2: Storage Configuration (5 points)
Configure storage tiers:
- Set up automatic migration rule: Hot → Warm after 30 days
- Configure quota warning at 80% usage
- Create storage report for all users

**Deliverables**:
- Configuration screenshots
- Migration rule details
- Storage usage report

### Task 1.3: System Monitoring (5 points)
Set up monitoring for the organization:
- Create custom dashboard in Grafana
- Configure alert for high error rate (>5%)
- Set up email notification for quota warnings

**Deliverables**:
- Grafana dashboard URL
- Alert configuration
- Test alert trigger

### Task 1.4: Basic Troubleshooting (5 points)
Resolve the following pre-configured issues:
- User "test.user@training.com" cannot login
- Upload showing "Unsupported format" for MP4 files
- Search returning no results for existing assets

**Deliverables**:
- Resolution steps for each issue
- Root cause identification
- Verification of fixes

---

## Part 2: Troubleshooting Scenarios (40 points)

### Scenario 2.1: Performance Crisis (10 points)
**Situation**: System performance has degraded significantly. Users report:
- Uploads taking 10x longer than normal
- Search queries timing out
- General UI sluggishness

**Your Task**:
1. Identify the root cause
2. Implement a fix
3. Verify performance restoration
4. Create monitoring to prevent recurrence

**Evaluation Criteria**:
- Systematic approach to diagnosis
- Correct identification of bottleneck
- Appropriate fix implementation
- Performance metrics before/after

### Scenario 2.2: Data Integrity Issue (10 points)
**Situation**: Several users report:
- Assets showing incorrect file sizes
- Some metadata fields are corrupted
- Version history is inconsistent

**Your Task**:
1. Assess the scope of corruption
2. Identify affected assets
3. Restore data integrity
4. Implement preventive measures

**Evaluation Criteria**:
- Data analysis accuracy
- Safe recovery procedures
- Minimal data loss
- Prevention strategy

### Scenario 2.3: Integration Failure (10 points)
**Situation**: Adobe Premiere Pro integration stopped working:
- Plugin cannot authenticate
- API returning 403 errors
- Affects 50+ editors currently working

**Your Task**:
1. Diagnose authentication issue
2. Restore integration functionality
3. Communicate with affected users
4. Document the solution

**Evaluation Criteria**:
- Quick problem identification
- Minimal downtime
- Clear communication
- Complete documentation

### Scenario 2.4: Multi-Service Outage (10 points)
**Situation**: Cascading failure affecting multiple services:
- Asset service is down
- Search service returning errors
- Proxy generation queue backing up

**Your Task**:
1. Identify failure sequence
2. Restore services in correct order
3. Clear backlogs safely
4. Perform root cause analysis

**Evaluation Criteria**:
- Understanding of service dependencies
- Correct recovery sequence
- System stability after recovery
- Comprehensive RCA

---

## Part 3: Emergency Response (25 points)

### Scenario 3.1: Security Incident (15 points)
**Situation**: Potential security breach detected:
- Unusual API access patterns from unknown IPs
- Multiple failed login attempts
- Suspicious file uploads detected

**Your Task**:
1. Assess security threat level
2. Implement immediate protective measures
3. Investigate breach extent
4. Create incident report

**Required Actions**:
- Block suspicious IPs
- Review access logs
- Check for compromised accounts
- Enable additional security measures
- Document timeline and actions

**Evaluation Criteria**:
- Speed of response
- Appropriate containment
- Thorough investigation
- Professional documentation

### Scenario 3.2: Critical Data Recovery (10 points)
**Situation**: Production database corruption after power outage:
- Primary database won't start
- Last backup is 4 hours old
- 200 users affected
- Live broadcast in 2 hours

**Your Task**:
1. Assess corruption extent
2. Execute recovery plan
3. Minimize data loss
4. Ensure system ready for broadcast

**Required Actions**:
- Attempt database repair
- Restore from backup if needed
- Recover transaction logs
- Verify system functionality
- Communicate status updates

**Evaluation Criteria**:
- Recovery speed
- Data loss minimization
- Communication clarity
- System readiness

---

## Part 4: Documentation (15 points)

### Task 4.1: Knowledge Base Article (5 points)
Create a KB article for one issue you resolved:
- Clear problem description
- Step-by-step solution
- Prevention tips
- Related articles

### Task 4.2: Incident Report (5 points)
Write a formal incident report for the security scenario:
- Executive summary
- Technical details
- Impact assessment
- Remediation steps
- Lessons learned

### Task 4.3: Standard Operating Procedure (5 points)
Create an SOP for one of the following:
- Weekly system maintenance
- New client onboarding
- Emergency service restart
- Backup verification

---

## Assessment Environment Details

### Available Test Accounts
```
Admin User: admin@training.com / TrainingAdmin123!
Editor User: editor@training.com / TrainingEdit123!
Viewer User: viewer@training.com / TrainingView123!
Test User: test.user@training.com / TestUser123!
```

### Service Endpoints
```
API Gateway: http://training.mams.com:8000
Asset Service: http://training.mams.com:8004
Search Service: http://training.mams.com:8006
Storage Service: http://training.mams.com:8002
```

### Database Access
```bash
# PostgreSQL
psql -h localhost -U mams_admin -d mams_training

# MongoDB
mongosh mongodb://localhost:27017/mams_training

# Redis
redis-cli -h localhost
```

### Useful Commands Cheat Sheet
```bash
# Check service health
curl http://localhost:8000/health

# View logs
tail -f /var/log/mams/*.log

# Service management
docker-compose ps
docker-compose restart [service]

# Database queries
psql -c "SELECT * FROM users WHERE email='test@example.com'"

# Clear caches
redis-cli FLUSHALL
```

---

## Submission Requirements

### Required Files
1. `assessment-results.md` - Summary of all completed tasks
2. `screenshots/` - Directory with all screenshots
3. `scripts/` - Any scripts you created
4. `reports/` - Incident reports and documentation

### Submission Format
```bash
# Create submission archive
tar -czf mams-assessment-[your-name].tar.gz \
  assessment-results.md \
  screenshots/ \
  scripts/ \
  reports/

# Upload to assessment portal
curl -X POST https://training.mams.com/submit \
  -F "file=@mams-assessment-[your-name].tar.gz" \
  -F "token=YOUR_ASSESSMENT_TOKEN"
```

---

## Evaluation Rubric

### Technical Skills (60%)
- Problem diagnosis accuracy
- Solution effectiveness
- Tool proficiency
- Best practices followed

### Process & Methodology (20%)
- Systematic approach
- Documentation quality
- Time management
- Safety considerations

### Communication (10%)
- Clarity of reports
- User communication
- Technical writing
- Status updates

### Innovation (10%)
- Creative solutions
- Efficiency improvements
- Preventive measures
- Knowledge sharing

---

## Tips for Success

1. **Read Everything First** - Understand all tasks before starting
2. **Manage Time** - Allocate time based on point values
3. **Document As You Go** - Don't leave documentation until the end
4. **Test Your Fixes** - Always verify solutions work
5. **Think Like Support** - Consider user impact and communication
6. **Use Available Resources** - Reference documentation and tools
7. **Stay Calm** - Emergency scenarios test composure
8. **Be Thorough** - Partial credit given for approach even if not complete

---

## Post-Assessment

### Results
- Available within 48 hours
- Detailed feedback provided
- Areas for improvement identified
- Certification level determined

### Retake Policy
- One retake allowed after 30 days
- Additional training recommended
- Different scenarios provided
- Same evaluation criteria

Good luck with your assessment!