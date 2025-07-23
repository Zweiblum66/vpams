# MAMS Support Certification Exam

## Exam Information

- **Duration**: 2 hours
- **Questions**: 60 questions
- **Passing Score**: 80% (48/60)
- **Format**: Multiple choice, scenario-based, practical exercises

## Instructions

1. Read each question carefully
2. Select the best answer(s)
3. Some questions may have multiple correct answers
4. Use the provided reference materials as needed
5. Submit your answers within the time limit

---

## Section 1: Platform Knowledge (15 questions)

### 1. What is the primary purpose of MAMS?
a) Email management  
b) Digital media asset management  
c) Project management  
d) Customer relationship management  

### 2. How many microservices comprise the MAMS architecture?
a) 8  
b) 10  
c) 13  
d) 15  

### 3. Which storage tiers are available in MAMS? (Select all that apply)
a) Hot  
b) Warm  
c) Cold  
d) Archive  
e) Express  

### 4. What is the default session timeout for MAMS?
a) 15 minutes  
b) 30 minutes  
c) 60 minutes  
d) 120 minutes  

### 5. Which authentication methods does MAMS support? (Select all that apply)
a) Local authentication  
b) LDAP  
c) SAML  
d) OAuth  
e) Biometric  

### 6. What is the maximum file size for upload via the web interface?
a) 10GB  
b) 50GB  
c) 100GB  
d) Unlimited  

### 7. Which database stores user information?
a) MongoDB  
b) PostgreSQL  
c) Redis  
d) OpenSearch  

### 8. What video formats are supported by MAMS? (Select all that apply)
a) MP4  
b) MOV  
c) MXF  
d) ProRes  
e) All of the above  

### 9. Which service handles video proxy generation?
a) Asset Management Service  
b) Storage Service  
c) Proxy Generation Service  
d) Workflow Engine  

### 10. What is the default API rate limit per user?
a) 100 requests/minute  
b) 1000 requests/minute  
c) 100 requests/hour  
d) 1000 requests/hour  

### 11. Which search capabilities does MAMS offer? (Select all that apply)
a) Full-text search  
b) Visual similarity  
c) Facial recognition  
d) Natural language  
e) Audio matching  

### 12. What is the purpose of the Workflow Engine?
a) User authentication  
b) File storage  
c) Process automation  
d) Search indexing  

### 13. Which port does the API Gateway use?
a) 80  
b) 443  
c) 8000  
d) 8080  

### 14. What is the minimum password length requirement?
a) 8 characters  
b) 10 characters  
c) 12 characters  
d) 16 characters  

### 15. Which monitoring tool does MAMS use for metrics?
a) Nagios  
b) Prometheus  
c) Datadog  
d) New Relic  

---

## Section 2: Troubleshooting (20 questions)

### 16. A user reports "Permission Denied" when accessing a project. What should you check first?
a) User's password  
b) User's role and project permissions  
c) System storage space  
d) Network connectivity  

### 17. Upload is stuck at 60%. What are the most likely causes? (Select all that apply)
a) Network interruption  
b) Storage quota exceeded  
c) File size limit reached  
d) Unsupported format  
e) Server maintenance  

### 18. How would you check if an asset is indexed in OpenSearch?
a) `SELECT * FROM assets WHERE indexed = true`  
b) `curl http://opensearch:9200/assets/_search?q=id:asset-uuid`  
c) `redis-cli GET asset:uuid`  
d) `docker logs opensearch | grep asset-uuid`  

### 19. A user cannot log in and receives "Account Locked". What SQL query would you use to unlock?
a) `DELETE FROM users WHERE email = 'user@example.com'`  
b) `UPDATE users SET status = 'active' WHERE email = 'user@example.com'`  
c) `UPDATE users SET locked_until = NULL WHERE email = 'user@example.com'`  
d) `INSERT INTO users (email, status) VALUES ('user@example.com', 'active')`  

### 20. Video playback fails. What should you check? (Select all that apply)
a) Proxy generation status  
b) Browser compatibility  
c) Network bandwidth  
d) Codec support  
e) User's email settings  

### 21. System performance is degraded. Which command shows Docker container resource usage?
a) `docker ps`  
b) `docker stats`  
c) `docker info`  
d) `docker resources`  

### 22. How do you find the 10 slowest database queries?
a) `SHOW SLOW QUERIES LIMIT 10`  
b) `SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10`  
c) `EXPLAIN ANALYZE ALL QUERIES`  
d) `SELECT query FROM slow_log LIMIT 10`  

### 23. A service is returning 502 Bad Gateway. What does this typically indicate?
a) User not authenticated  
b) Backend service is down  
c) Rate limit exceeded  
d) Invalid request format  

### 24. How would you safely restart a service with minimal disruption?
a) `docker kill service && docker start service`  
b) `docker restart service`  
c) Enable maintenance mode, wait for requests, restart, disable maintenance  
d) `systemctl restart docker`  

### 25. Search returns no results but asset exists. What's the first troubleshooting step?
a) Restart OpenSearch  
b) Check if asset is indexed  
c) Clear all caches  
d) Reboot the server  

### 26. How do you identify which service is causing high CPU usage?
a) `top`  
b) `docker stats`  
c) `ps aux | sort -k3 -rn`  
d) All of the above  

### 27. Upload fails with "Unsupported Format". How do you add support for a new format?
a) Edit the source code  
b) Update format configuration via admin API  
c) Restart the upload service  
d) Contact development team only  

### 28. Database connection pool is exhausted. What's the immediate fix?
a) Restart database  
b) Increase pool size and restart service  
c) Delete all connections  
d) Disable connection pooling  

### 29. How do you trace a request across multiple services?
a) Check each service log individually  
b) Use grep with timestamp  
c) Use trace ID in distributed tracing  
d) Monitor network traffic  

### 30. Storage is at 95% capacity. What are appropriate actions? (Select all that apply)
a) Delete random files  
b) Move old assets to cold storage  
c) Increase storage quota  
d) Clean up orphaned files  
e) Archive completed projects  

### 31. MFA token is not working. What should you verify?
a) User's password  
b) Device time synchronization  
c) Network connectivity  
d) Browser cookies  

### 32. Workflow is stuck in processing. How do you investigate?
a) Check workflow logs  
b) View workflow status  
c) Verify dependent services  
d) All of the above  

### 33. Redis cache is growing unbounded. What's the likely cause?
a) No TTL set on keys  
b) Redis is corrupted  
c) Network issues  
d) CPU overload  

### 34. How do you emergency flush all caches?
a) `redis-cli FLUSHALL`  
b) `cache --clear-all`  
c) Restart Redis service  
d) Both a and c  

### 35. User reports data loss after system update. What's your first action?
a) Blame the developers  
b) Check backup availability  
c) Restart all services  
d) Tell user data is gone  

---

## Section 3: Customer Service (10 questions)

### 36. A frustrated customer says "This system never works!" How do you respond?
a) "It works fine for everyone else"  
b) "I understand your frustration. Let me help resolve this issue"  
c) "You must be doing something wrong"  
d) "Have you tried turning it off and on?"  

### 37. When should you escalate a ticket to Level 2?
a) Whenever a customer asks  
b) After 5 minutes  
c) When issue requires system configuration changes  
d) At end of your shift  

### 38. How long should initial response to a P1 incident take?
a) 5 minutes  
b) 15 minutes  
c) 1 hour  
d) 24 hours  

### 39. What information is essential when creating a ticket? (Select all that apply)
a) User details  
b) Error messages  
c) Steps to reproduce  
d) User's birthday  
e) Time of occurrence  

### 40. A VIP customer demands immediate attention for a minor issue. How do you handle?
a) Drop everything for them  
b) Acknowledge their importance while following proper prioritization  
c) Tell them to wait like everyone else  
d) Escalate immediately to management  

### 41. When writing a technical solution for non-technical users, you should:
a) Use as much jargon as possible  
b) Skip explanations  
c) Use simple language and analogies  
d) Only provide command lines  

### 42. How often should you update customers on long-running issues?
a) Only when resolved  
b) Every 30 minutes  
c) At agreed intervals or when status changes  
d) Never - they'll ask if needed  

### 43. A customer is confused by your explanation. What's the best approach?
a) Repeat the same explanation louder  
b) Tell them to read the manual  
c) Try a different explanation approach  
d) Escalate to someone else  

### 44. What's the appropriate way to say "no" to an impossible request?
a) "That's impossible"  
b) "I understand what you need. Here's what we can do instead..."  
c) "Not my problem"  
d) "Submit a feature request"  

### 45. After resolving an issue, when should you follow up?
a) Never  
b) Within 24-48 hours  
c) After one week  
d) After one month  

---

## Section 4: System Administration (10 questions)

### 46. How do you create a custom role with specific permissions?
a) Edit configuration file  
b) Use SQL INSERT into roles table  
c) Through admin UI only  
d) Contact development team  

### 47. What's the correct order for system maintenance?
a) Notify users → Backup → Maintenance → Test → Resume  
b) Maintenance → Notify users → Test  
c) Backup → Maintenance → Notify users  
d) Random order is fine  

### 48. How often should database backups be tested?
a) Never  
b) Monthly  
c) Quarterly  
d) Only when needed  

### 49. What's the SQL to find users who haven't logged in for 90 days?
a) `SELECT * FROM users WHERE last_login < NOW()`  
b) `SELECT * FROM users WHERE last_login < NOW() - INTERVAL '90 days'`  
c) `SELECT * FROM users WHERE login_count = 0`  
d) `DELETE FROM users WHERE old = true`  

### 50. Which tasks should be in daily maintenance? (Select all that apply)
a) Check system health  
b) Review error logs  
c) Full system reboot  
d) Verify backup completion  
e) Update all software  

### 51. How do you safely increase a service's resource allocation?
a) Edit Docker compose and restart  
b) Kill service and start with more resources  
c) Test in staging, plan window, apply change, monitor  
d) Let it fail first  

### 52. What indicates a possible security breach?
a) High CPU usage  
b) Multiple failed login attempts from various IPs  
c) Large file uploads  
d) Many search queries  

### 53. How do you configure email notifications?
a) Hard-code in application  
b) Environment variables and admin API  
c) Direct database update  
d) Email vendor portal only  

### 54. Storage tier migration should be done:
a) Randomly  
b) Based on age and access patterns  
c) Never  
d) Only when storage is full  

### 55. What's the impact of running VACUUM FULL on PostgreSQL?
a) No impact  
b) Improves performance instantly  
c) Locks tables during operation  
d) Deletes old data  

---

## Section 5: Practical Scenarios (5 questions)

### 56. Scenario: Monday morning, multiple users report system is "very slow". Describe your troubleshooting approach in order:

[Write your answer - 5 steps minimum]

### 57. Scenario: A broadcast company needs to upload 500TB of archive footage in 2 weeks. What's your recommendation?

[Write your answer - Include technical approach and alternatives]

### 58. Scenario: Production database accidentally deleted. You have backups from 6 hours ago. Describe recovery process:

[Write your answer - Include steps and time estimates]

### 59. Scenario: Major client's integration stopped working after weekend maintenance. They have a live broadcast in 3 hours. What's your action plan?

[Write your answer - Include immediate actions and communication]

### 60. Scenario: You discover a service has been mining cryptocurrency. Describe your incident response:

[Write your answer - Include security, communication, and remediation steps]

---

## Answer Key and Scoring

### Section 1: Platform Knowledge (1 point each)
1. b  
2. c  
3. a,b,c,d  
4. c  
5. a,b,c,d  
6. c  
7. b  
8. e  
9. c  
10. b  
11. a,b,c,d,e  
12. c  
13. c  
14. c  
15. b  

### Section 2: Troubleshooting (2 points each)
16. b  
17. a,b,c,d  
18. b  
19. c  
20. a,b,c,d  
21. b  
22. b  
23. b  
24. c  
25. b  
26. d  
27. b  
28. b  
29. c  
30. b,d,e  
31. b  
32. d  
33. a  
34. a  
35. b  

### Section 3: Customer Service (1 point each)
36. b  
37. c  
38. b  
39. a,b,c,e  
40. b  
41. c  
42. c  
43. c  
44. b  
45. b  

### Section 4: System Administration (1 point each)
46. b  
47. a  
48. b  
49. b  
50. a,b,d  
51. c  
52. b  
53. b  
54. b  
55. c  

### Section 5: Practical Scenarios (5 points each)
Evaluated based on:
- Completeness
- Technical accuracy
- Proper prioritization
- Communication considerations
- Best practices followed

## Certification Levels

- **90-100%**: Expert Level Certification
- **80-89%**: Professional Level Certification
- **70-79%**: Associate Level (retake recommended)
- **Below 70%**: Additional training required

Good luck!