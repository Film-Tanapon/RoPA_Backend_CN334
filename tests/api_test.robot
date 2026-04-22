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
    
Verify Create New Patient
    [Documentation]    ทดสอบการสร้างข้อมูลผู้ใช้ทั้งหมดจาก API
    ${payload}=    Create Dictionary    username=Robot    email=robottest@gmail.com   password_hash=Test    fullname=RobotTest    tel=1234567892    role=Admin    departments=BackendDev    status=active
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    POST On Session    api_session    /users    json=${payload}    headers=${headers}
    Status Should Be    200    ${response}

    ${new_user_id}=    Set Variable    ${response.json()['id']}
    Set Suite Variable    ${CREATED_USER_ID}    ${new_user_id}