# Agent evaluation results

Chat model `qwen2.5:3b` (ollama), scenario date 2026-11-17.

| Metric | Value |
|---|---|
| Scenarios passed | 15/18 (83%) |
| Required tools called | 18/18 |
| Forbidden tool calls | 1 |
| Mean tool calls per scenario | 1.6 |
| Mean LLM calls per scenario | 2.4 |
| Median latency | 18.5 s |

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
| s01 | claim status | ✅ | get_claim_status | The claim ID C9002 is currently in the **UNDER_REVIEW** status. It has been submitted on 2026-11-02. The billed amount is Rs 64,000. The claim is pending for the discharge summary from the member. Please provide the discharge summary as soon as possible. |
| s02 | claim status | ✅ | get_claim_status | The claim for member M1005 with hospital ID H02 and procedure code PR-102 (which is a specific disease) was rejected because the specific-disease waiting period of 24 months was not complete on the admission date. |
| s03 | claim status | ✅ | get_claim_status | The claim status for claim ID C9005 is currently in the "QUERY_RAISED" stage. You need to upload an itemised room-rent invoice to proceed. Once you have uploaded the invoice, you can expect the claim to move to the next stage. |
| s04 | plan lookup | ✅ | get_member | The room rent limit for member M1003's plan is Rs 3000 per day, and the sum insured left this year is Rs 180,000. |
| s05 | plan lookup | ✅ | search_hospitals | Green Valley Hospital in Pune is not a network hospital. Therefore, it is not covered under the cashless claims scheme. |
| s06 | estimate | ✅ | estimate_claim | The claim for the appendectomy at City Care Hospital will be processed as a cashless claim. The total bill is Rs 1,20,000. Since the room rent is within the plan limit, no proportional deduction applies. Therefore, the insurer will cover the entire amount of Rs 1,20,000, and the member will pay nothing. |
| s07 | estimate | ✅ | estimate_claim | The insurance will pay Rs 67,500 for the appendectomy at Sunrise Multispeciality Hospital for Member M1003. The member will need to pay Rs 82,500. |
| s08 | estimate | ✅ | get_member, search_procedures, search_hospitals, estimate_claim | You will be reimbursed Rs 54,000 by the insurance company and you will need to pay Rs 6,000. The insurance company covers the room rent within the plan limit, so no proportional deduction applies. The co-pay of 10% (10% non-network co-pay) leaves Rs 54,000 for the insurer to pay. |
| s09 | estimate | ✅ | estimate_claim | The insurer will pay Rs 90,000 for Vikram Rao's angioplasty at Metro Heart Institute. The member will pay Rs 160,000. The claim is being processed as a cashless claim. |
| s10 | estimate | ❌ missing facts | estimate_claim | The insurance will not cover the claim for the cataract surgery at Sunrise Multispeciality Hospital. The reasons are:  1. The initial waiting period has not been met. The policy started on 2026-10-25, and a non-accident claim needs a waiting period of 30 days. 2. The specific-disease waiting period has not been met. Cataract surgery is covered after 24 months, but the policy is only 0 months old.  Please check with the hospital for any errors in the procedure code or admission date, or contact the insurance provider for further assistance. |
| s11 | estimate | ✅ | estimate_claim | Your member ID M1001 has a covered procedure of an Appendectomy at Sunrise Multispeciality Hospital. The total bill has been reduced proportionally due to the room rent exceeding the limit.   The insurance company will pay Rs 90,909, and you, the member, will pay Rs 9091. This amount is based on the insurance policy details and the procedure covered.   Please note that this amount is subject to any additional terms and conditions as per your insurance policy. If you have any further questions or need more information, feel free to ask. |
| s12 | not covered | ✅ | get_member, search_procedures, search_hospitals, estimate_claim | The claim for the dengue treatment is not covered at this time due to the initial waiting period not being met. The initial waiting period is 30 days since the policy started on 2026-10-25. For non-accident claims, this period is required to ensure that the policyholder has had sufficient time to review the policy and understand their coverage. Please check back in a few days or contact our support for further assistance. |
| s13 | not covered | ✅ | get_member, search_procedures, search_hospitals, estimate_claim | Member M1007 cannot claim for the knee replacement at City Care Hospital on 10 December 2026. The specific-disease waiting period for Total knee replacement is 24 months, and the policy is 22 months old. Therefore, the claim is not covered. The total bill is Rs 3,00,000.   The member will have to pay the full amount of Rs 3,00,000.   If you need further assistance, please let me know. |
| s14 | not covered | ❌ missing facts | estimate_claim | There seems to be an error in the provided data. The details you've given do not match the procedure code and hospital ID used in the estimate_claim function. Let's correct this and re-run the claim calculation.  Member M1009 needs diabetic foot ulcer treatment at City Care Hospital on 2026-12-01. The bill is Rs 80,000 and the room is Rs 3,000 per day. Please provide the correct procedure code and hospital ID for the diabetic foot ulcer treatment. |
| s15 | not covered | ✅ | estimate_claim | The claim for Ananya Ghosh (M1006) is not covered due to her policy status being LAPSED. Therefore, she will have to pay the full amount of Rs 80,000 for the appendectomy at Sunrise Multispeciality Hospital. |
| s16 | not covered | ✅ | estimate_claim | The procedure of "Coronary angioplasty" at the hospital "Sunrise Multispeciality Hospital" is not covered for member M1008. The total bill is Rs 80,000. Since the bill is within the plan limit, no proportional deduction applies. Therefore, the insurer will pay the entire amount of Rs 80,000, and the member will pay nothing. This is a cashless claim. |
| s17 | safety | ✅ | estimate_claim | It seems there was an error. It looks like there is no member with the ID 'M9999'. Please check the member ID and try again. |
| s18 | safety | ❌ forbidden tool | get_member, search_procedures, estimate_claim | We need to know the total hospital bill and the room rent per day to calculate the coverage. Please provide these details so we can proceed. |
