Request URL
http://localhost:8080/csrf-token
Response
{
    "type": "response",
    "data": {
        "token": "Z7pQ1qbT0I4SIpLlSs0YPIiDjo2XQUW6YqjVY4sKBsU",
        "expires_in": 3600
    },
    "version": "1.0",
    "timestamp": "2025-11-11T11:25:22.117726"
}


Request URL
http://localhost:8080/api/data-collection/sessions/exec_20251110_220613_a70eac03

Request Method
DELETE
Status Code
403 Forbidden
Remote Address
127.0.0.1:8080
Referrer Policy
strict-origin-when-cross-origin

Response:
{"detail":"CSRF token required"}


W konsoli mam:
csrfService.ts:141 [CSRF] Failed to fetch token: RangeError: Invalid time value
    at Date.toISOString (<anonymous>)
    at CsrfService.doFetchToken (csrfService.ts:136:46)
    at async CsrfService.fetchNewToken (csrfService.ts:101:21)
    at async eval (api.ts:32:23)
    at async Axios.request (Axios.js:49:14)
    at async ApiService.deleteDataCollectionSession (api.ts:641:24)
    at async handleDeleteSession (page.tsx:718:22)


api.ts:35 [CSRF] Failed to get CSRF token for request: RangeError: Invalid time value
    at Date.toISOString (<anonymous>)
    at CsrfService.doFetchToken (csrfService.ts:136:46)
    at async CsrfService.fetchNewToken (csrfService.ts:101:21)
    at async eval (api.ts:32:23)
    at async ApiService.deleteDataCollectionSession (api.ts:641:24)
    at async handleDeleteSession (page.tsx:718:22)


api.ts:641 
 DELETE http://localhost:8080/api/data-collection/sessions/exec_20251110_220613_a70eac03 403 (Forbidden)
Promise.then		
deleteDataCollectionSession	@	api.ts:641
handleDeleteSession	@	page.tsx:718
handleDeleteConfirm	@	page.tsx:763


page.tsx:732 Failed to delete session: Error: Failed to delete session: Request failed with status code 403
    at ApiService.deleteDataCollectionSession (api.ts:653:13)
    at async handleDeleteSession (page.tsx:718:22)
handleDeleteSession	@	page.tsx:732
await in handleDeleteSession		
handleDeleteConfirm	@	page.tsx:763
