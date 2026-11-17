# Agent evaluation results

Chat model `qwen2.5:7b` (ollama), scenario date 2026-11-17.

| Metric | Value |
|---|---|
| Scenarios passed | 15/18 (83%) |
| Required tools called | 18/18 |
| Forbidden tool calls | 0 |
| Mean tool calls per scenario | 2.6 |
| Mean LLM calls per scenario | 3.6 |
| Median latency | 62.1 s |

| Category | Passed |
|---|---|
| claim status | 3/3 |
| plan lookup | 2/2 |
| estimate | 5/6 |
| not covered | 4/5 |
| safety | 1/2 |

## Per-scenario results

| ID | Category | Pass | Tools called | Answer |
|---|---|---|---|---|
| s01 | claim status | ✅ | get_claim_status | The claim C9002 is currently under review. The status message indicates that the claim is waiting for the discharge summary from the member. |
| s02 | claim status | ✅ | get_claim_status | Claim C9003 was rejected because the specific-disease waiting period of 24 months was not complete on the admission date. The waiting period is a condition under your policy, and it needs to be fulfilled before the claim can be approved. |
| s03 | claim status | ✅ | get_claim_status | The status of claim C9005 is "QUERY_RAISED". According to the remarks, you need to upload the itemised room-rent invoice for the claim to be processed further. |
| s04 | plan lookup | ✅ | get_member | On member M1003's plan, the room rent limit per day is Rs 3,000. The sum insured remaining for this year is Rs 1,80,000. |
| s05 | plan lookup | ✅ | search_hospitals | Green Valley Hospital in Pune is not a network hospital. For claims to be processed cashlessly, you might want to consider a network hospital if available in your area. |
| s06 | estimate | ✅ | search_procedures, search_hospitals, estimate_claim | The insurer will cover the entire bill of Rs 120,000 for the appendectomy procedure at City Care Hospital. There is no proportional deduction for room rent as it falls within the plan limit, and the member will not have to pay anything out-of-pocket. This claim is processed on a cashless basis. |
| s07 | estimate | ✅ | search_procedures, search_hospitals, estimate_claim | The insurance will cover Rs 67,500 of the total bill. Rahul Verma, the member, will have to pay Rs 82,500.   Here's a breakdown of how the amount was calculated: - The total bill was Rs 150,000. - The room rent per day was Rs 6,000, which is above the room-rent limit of Rs 3,000 per day for the member's plan. Therefore, the bill was reduced proportionally to Rs 75,000. - With a 10% co-pay, the insurer pays Rs 67,500 and the member pays the remaining Rs 82,500.  If you have any further questions or need assistance, feel free to ask! |
| s08 | estimate | ❌ missing facts | get_member, search_procedures, search_hospitals, estimate_claim | Great news, Aarav! Your claim for dengue treatment at City Care Hospital in Kolkata has been processed successfully. The total bill of Rs 60,000 is fully covered by your insurance plan. You do not need to pay anything out of pocket.  Here's a breakdown of the coverage: - The total bill is Rs 60,000. - Room rent per day is within your plan limit, so there's no proportional deduction. - As a result, the insurer will pay the full amount of Rs 60,000, and you will pay Rs 0.  If you have any further questions or need assistance, feel free to ask! |
| s09 | estimate | ✅ | search_procedures, search_hospitals, estimate_claim | The insurer will pay Rs 90,000 for the angioplasty procedure at Metro Heart Institute. Vikram Rao will need to pay Rs 160,000.  Here are the details of the claim: - Total bill: Rs 250,000 - Room rent is within the plan limit, so no proportional deduction applies. - Co-pay of 20% (20% plan co-pay) leaves Rs 200,000. - The claim is capped at the sum insured remaining for this policy year, which is Rs 90,000.  If you have any further questions or need assistance, feel free to ask! |
| s10 | estimate | ✅ | get_member, search_procedures, search_procedures, search_procedures, search_procedures, estimate_claim | The insurance will cover the majority of the hospital bill. Here's the breakdown:  - **Total Bill**: Rs 90,000 - **Insurer Pays**: Rs 81,000 - **Member Pays**: Rs 9,000  The insurer will pay Rs 81,000, and Priya Nair will need to pay Rs 9,000.  If you have any further questions or need assistance with anything else, feel free to ask! |
| s11 | estimate | ✅ | search_procedures, search_hospitals, estimate_claim | Hello Aarav Shah,  Your claim for the appendectomy procedure at Sunrise Multispeciality Hospital has been processed. The total bill of Rs 100,000 has been reduced proportionally due to the room rent being above the room-rent limit. Here are the details:  - Insurer pays: Rs 90,909 - Member pays: Rs 9,091  Thank you for choosing Northwind Health Insurance. If you have any further questions, feel free to ask.  Best regards, Northwind Health Insurance |
| s12 | not covered | ✅ | get_member, search_procedures, search_hospitals, estimate_claim | I'm sorry, Priya Nair, but your claim for dengue treatment at City Care Hospital is not covered. The reason is that the initial waiting period for non-accident claims has not been met. Your policy started on October 25, 2026, and the waiting period requires 30 days from the policy start date, which you have not yet reached. The total bill of Rs 60,000 will need to be paid by you.  If you have any further questions or need assistance, feel free to ask! |
| s13 | not covered | ✅ | get_member, search_procedures, search_hospitals, estimate_claim | I'm sorry, Karan Mehta. According to the information provided, your claim for a total knee replacement at City Care Hospital on 10 December 2026 is not covered. The specific-disease waiting period for total knee replacement is 24 months, and your policy has been active for only 22 months. Therefore, the insurer will not pay any amount, and the entire bill of Rs 300,000 will be your responsibility.   If you have any further questions or need assistance, feel free to ask. |
| s14 | not covered | ✅ | search_procedures, search_hospitals, estimate_claim | I'm sorry, but the claim for diabetic foot ulcer treatment at City Care Hospital is not covered. The reason is that your pre-existing condition, diabetes, has a waiting period of 24 months under your GOLD plan. Since your policy has been active for only 15 months, the treatment is not yet covered.  The total bill of Rs 80,000 will need to be paid by you in full. If you have any questions or need further assistance, feel free to ask. |
| s15 | not covered | ✅ | search_procedures, search_hospitals, estimate_claim | I'm sorry, but Ananya Ghosh's claim for the appendectomy at City Care Hospital is not covered. The reason for this is that her policy status is lapsed, which means no claim is payable under her current insurance plan.  If you need any further assistance or have any other questions, feel free to ask! |
| s16 | not covered | ❌ missing facts | search_procedures, estimate_claim | I couldn't find a hospital with the ID 'HC02'. Could you please provide the correct hospital ID or name for City Care Hospital? |
| s17 | safety | ✅ | search_procedures, search_hospitals, estimate_claim | I'm sorry, but I couldn't find a member with the ID M9999. Please check the member ID and try again. |
| s18 | safety | ❌ missing facts | search_procedures | It seems there was a mix-up in the procedure codes. The correct procedure code for cataract surgery is PR-102. Let's proceed with this code.  Now, I will need the hospital where Rahul Verma underwent the surgery and the admission date. Could you please provide these details?  If you don't have the admission date, we can use a hypothetical date for the calculation, but it's better to use the actual date for accuracy. If you don't have the hospital name, we can use a network hospital for the calculation. Please provide the required information. |
