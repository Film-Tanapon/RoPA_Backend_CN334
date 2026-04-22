*** Settings ***
Library     RequestsLibrary
Library     Collections
Suite Setup     Create Session    api_session    ${BASE_URL}

*** Variables ***
# ใชชื่อ service 'api-server' (หรือชื่อที่ตั้งไวใน docker-compose) และใช port ภายในของ docker-compose คือ 8000 แทนที่จะใช 3340
${BASE_URL}     http://api-server:8000

*** Test Cases ***
Verify Get All Patients Successfully
    [Documentation]    ทดสอบการดึงข้อมูลผู้ใช้ทั้งหมดจาก API
    Create Session    api_session    ${BASE_URL}
    ${response}=    GET On Session    api_session    /users
    Status Should Be    200    ${response}
    Log To Console    \nResponse Data: ${response.json()}