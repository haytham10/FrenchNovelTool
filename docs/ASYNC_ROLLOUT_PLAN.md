# Async PDF Processing - Rollout Plan

## Overview

This document outlines the safe deployment and rollout strategy for the async PDF processing feature. The goal is to minimize risk while ensuring a smooth transition from synchronous to asynchronous processing.

## Rollout Phases

### Phase 1: Infrastructure Deployment (Week 1)

**Objective**: Deploy async infrastructure without impacting existing users

**Tasks**:
- [x] Deploy Redis to production
- [x] Deploy Celery workers (2 workers initially)
- [x] Deploy Flower monitoring UI (restricted access)
- [ ] Run database migrations (`flask db upgrade`)
- [ ] Verify all services are healthy
- [ ] Run smoke tests

**Success Criteria**:
- ✅ Redis is running and accessible
- ✅ Celery workers are processing test tasks
- ✅ Flower UI is accessible
- ✅ Database migration completed without errors
- ✅ All existing sync endpoints still work

**Rollback Plan**:
- Stop Celery workers
- Remove async endpoints from load balancer
- Revert database migration if needed

---

### Phase 2: Internal Testing (Week 2)

**Objective**: Test async processing with internal team

**Tasks**:
- [ ] Create feature flag: `ASYNC_PROCESSING_ENABLED`
- [ ] Enable async for internal test accounts only
- [ ] Test with various PDF sizes (30, 100, 300, 500 pages)
- [ ] Test error scenarios:
  - API failures
  - Job cancellation
  - Worker crashes
  - Network timeouts
- [ ] Monitor metrics:
  - Task success rate
  - Processing time
  - Memory usage
  - Credit refund accuracy

**Test Cases**:
1. Small PDF (< 30 pages) → Single chunk processing
2. Medium PDF (50-100 pages) → Multi-chunk processing
3. Large PDF (300+ pages) → Parallel chunk processing
4. Cancel job mid-processing
5. Network failure during processing
6. Gemini API rate limit error

**Success Criteria**:
- ✅ 95%+ success rate for internal tests
- ✅ No data loss or credit issues
- ✅ Progress tracking works correctly
- ✅ Cancellation works reliably
- ✅ Error messages are user-friendly

**Rollback Plan**:
- Disable feature flag for test accounts
- Continue using sync processing

---

### Phase 3: Beta Rollout (Week 3-4)

**Objective**: Gradually roll out to production users

**Implementation**:
```python
# Feature flag logic in routes.py
def should_use_async_processing(user_id: int, pdf_size_mb: float) -> bool:
    # Always use async for large files
    if pdf_size_mb > 10:
        return True
    
    # Gradual rollout based on user_id
    rollout_percentage = get_rollout_percentage()  # From config
    return (user_id % 100) < rollout_percentage
```

**Rollout Schedule**:
- Week 3, Day 1-2: 10% of users
- Week 3, Day 3-4: 25% of users
- Week 3, Day 5-7: 50% of users
- Week 4, Day 1-3: 75% of users
- Week 4, Day 4-7: 100% of users

**Monitoring**:
- Track metrics per rollout cohort:
  - Success rate
  - Processing time
  - Error rate
  - User satisfaction (support tickets)
- Set alerts:
  - Error rate > 5%
  - Processing time > 10 min for 300-page PDF
  - Worker queue depth > 100

**Rollback Triggers**:
- Error rate > 10%
- Multiple user complaints
- System instability (workers crashing)
- Data integrity issues

**Rollback Procedure**:
1. Reduce rollout percentage immediately
2. Investigate root cause
3. Fix issue in staging
4. Resume rollout after verification

---

### Phase 4: Full Deployment (Week 5)

**Objective**: Complete migration to async processing

**Tasks**:
- [ ] Enable async for 100% of users
- [ ] Deprecate sync endpoint with warning
- [ ] Update documentation
- [ ] Monitor for 1 week

**Success Criteria**:
- ✅ All users successfully migrated
- ✅ No increase in support tickets
- ✅ System metrics stable
- ✅ Credit system accurate

---

### Phase 5: Cleanup (Week 6+)

**Objective**: Remove legacy sync code

**Tasks**:
- [ ] Archive sync processing code
- [ ] Remove feature flags
- [ ] Update tests
- [ ] Document lessons learned

---

## Monitoring & Alerts

### Key Metrics

**System Health**:
- Celery worker uptime
- Redis memory usage
- Task queue depth
- Worker CPU/memory usage

**Processing Metrics**:
- Task success rate (target: > 95%)
- Average processing time by PDF size
- Chunk failure rate
- Credit refund accuracy

**User Experience**:
- Time to job completion
- Cancellation rate
- Support ticket volume
- User retention

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 3% | > 10% |
| Queue depth | > 50 | > 100 |
| Worker downtime | > 5 min | > 15 min |
| Processing time (300p) | > 8 min | > 15 min |
| Memory usage | > 80% | > 95% |

### Dashboards

**Flower**: http://localhost:5555
- Real-time task monitoring
- Worker status
- Task history

**Application Logs**:
```bash
# View Celery worker logs
docker-compose logs -f celery-worker

# View backend logs
docker-compose logs -f backend

# View failed tasks
celery -A app.celery_app:celery inspect active
celery -A app.celery_app:celery inspect reserved
```

---

## Risk Mitigation

### Data Integrity
- ✅ Jobs reserve credits before processing
- ✅ Automatic refunds on failure/cancellation
- ✅ Partial results saved even on chunk failures
- ✅ Database transactions for all state changes

### Reliability
- ✅ Automatic retry for transient failures
- ✅ Task timeout protection
- ✅ Worker crash recovery (acks_late)
- ✅ Redis persistence enabled

### Security
- ✅ Authentication required for all endpoints
- ✅ Rate limiting enabled
- ✅ Temporary files auto-cleanup
- ✅ Flower UI password-protected (production)

### Performance
- ✅ Parallel chunk processing
- ✅ Worker concurrency tuning
- ✅ Redis memory limits
- ✅ Worker memory leak prevention (max_tasks_per_child)

---

## Rollback Procedures

### Emergency Rollback (< 5 minutes)

1. **Disable async processing**:
   ```bash
   # Set environment variable
   export ASYNC_PROCESSING_ENABLED=false
   
   # Restart backend
   docker-compose restart backend
   ```

2. **Stop accepting new async jobs**:
   ```bash
   # Update routes.py to return 503
   # Or use load balancer to block /process-pdf-async
   ```

3. **Wait for in-flight jobs to complete** (max 30 min)

4. **Verify sync processing works**

### Controlled Rollback (< 1 hour)

1. **Reduce rollout percentage**:
   ```python
   # In config.py or admin panel
   ASYNC_ROLLOUT_PERCENTAGE = 0  # Or 10%, 25%, etc.
   ```

2. **Monitor metrics** to confirm issue is resolved

3. **Investigate and fix** root cause

4. **Test fix** in staging environment

5. **Resume rollout** once verified

### Full Rollback (< 4 hours)

1. **Stop all Celery workers**:
   ```bash
   docker-compose stop celery-worker flower
   ```

2. **Revert database migration** (if needed):
   ```bash
   flask db downgrade -1
   ```

3. **Remove async endpoints** from code

4. **Deploy previous version**

5. **Verify system stability**

---

## Success Metrics

### Technical Metrics
- **Availability**: > 99.9%
- **Success Rate**: > 95%
- **Processing Time**: < 5 min for 300-page PDF
- **Error Rate**: < 5%

### Business Metrics
- **User Satisfaction**: Positive feedback from beta users
- **Support Tickets**: No increase in volume
- **Retention**: No drop in user retention
- **Credit Accuracy**: 100% (no credit discrepancies)

### Performance Metrics
- **Throughput**: 100+ PDFs per hour
- **Latency**: < 2s for job creation
- **Scalability**: Linearly scalable with worker count

---

## Post-Deployment Review

### Week 1 Review
- Analyze metrics
- Review support tickets
- Collect user feedback
- Identify optimization opportunities

### Week 4 Review
- Compare sync vs async performance
- Document lessons learned
- Update documentation
- Plan future improvements

### Month 3 Review
- Analyze cost impact
- Review scalability
- Plan advanced features:
  - WebSocket for real-time updates
  - Priority queues for premium users
  - Auto-scaling workers

---

## Communication Plan

### Internal Team
- Daily standups during rollout
- Slack channel for async rollout
- On-call rotation for incident response

### Users
- **Beta announcement**: Email to selected users
- **Feature release**: Blog post + in-app notification
- **Migration notice**: Email 1 week before deprecating sync
- **Deprecation notice**: In-app warning for sync endpoint

### Support Team
- Training on new feature
- FAQ document
- Troubleshooting guide
- Escalation procedures

---

## Dependencies

### Infrastructure
- [x] Redis deployment
- [x] Celery workers
- [x] Flower monitoring
- [ ] Database migration
- [ ] Load balancer configuration

### Code
- [x] Backend implementation
- [x] Frontend integration
- [x] Tests
- [x] Documentation

### External Services
- [x] Gemini API access
- [x] Google Sheets API access

---

## Contacts

**On-Call**: TBD
**Product Owner**: TBD
**Engineering Lead**: TBD
**DevOps**: TBD

---

## Appendix: Troubleshooting

### Common Issues

**Workers not processing tasks**:
- Check Redis connection
- Verify worker is running: `celery -A app.celery_app:celery inspect active`
- Check worker logs: `docker-compose logs celery-worker`

**High memory usage**:
- Reduce worker concurrency
- Decrease chunk size
- Lower `max_tasks_per_child`

**Tasks stuck in pending**:
- Check queue depth in Flower
- Scale up workers
- Check Redis memory

**Credit refunds not working**:
- Check database logs
- Verify credit_service logic
- Review failed job records

---

**Last Updated**: 2025-10-04
**Version**: 1.0
**Status**: Ready for Phase 1
