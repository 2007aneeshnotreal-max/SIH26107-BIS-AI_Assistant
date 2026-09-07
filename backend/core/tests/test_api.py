import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

@pytest.fixture
def client(db):
    call_command("seed_demo_data",verbosity=0)
    return APIClient()

def test_chat_returns_valid_citation(client):
    session=client.post("/api/chat/sessions/",{"audience":"industry","language":"en"},format="json").json()
    response=client.post(f"/api/chat/sessions/{session['public_id']}/messages/",{"message":"Which standard applies to an electric kettle?","language":"en"},format="json")
    assert response.status_code==201
    assert response.json()["citations"][0]["standard_number"]=="IS 367:1993"

def test_verification_is_labelled_mock(client):
    response=client.post("/api/verification/check/",{"identifier":"CM/L-1234567890"},format="json")
    assert response.json()["found"] is True
    assert response.json()["official"] is False

def test_recommendation(client):
    response=client.post("/api/standards/recommend/",{"product_description":"domestic pressure cooker","category":"utensil"},format="json")
    assert response.status_code==200
    assert response.json()["results"][0]["number"]=="IS 2347:2023"

def test_guest_is_limited_after_six_questions(client):
    session=client.post("/api/chat/sessions/",{"audience":"industry","language":"en"},format="json").json()
    url=f"/api/chat/sessions/{session['public_id']}/messages/"
    for question in ("electric kettle","toothpaste","pressure cooker","sandals","microwave oven","washing machine"):
        assert client.post(url,{"message":question,"language":"en"},format="json").status_code==201
    response=client.post(url,{"message":"gold jewellery","language":"en"},format="json")
    assert response.status_code==403
    assert response.json()["error"]["code"]=="login_required"

def test_product_image_requests_brand_when_product_is_detected(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER","mock")
    session=client.post("/api/chat/sessions/",{"audience":"industry","language":"en"},format="json").json()
    image=SimpleUploadedFile("electric-kettle.jpg",b"demo-image",content_type="image/jpeg")
    response=client.post(f"/api/chat/sessions/{session['public_id']}/images/",{"image":image,"language":"en"},format="multipart")
    assert response.status_code==201
    assert response.json()["intent"]=="product_image_clarification"
    assert "company or brand" in response.json()["content"]

def test_old_brand_prompt_does_not_hijack_stage_or_lab_actions(client, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    session=client.post("/api/chat/sessions/",{"audience":"industry","language":"en"},format="json").json()
    image=SimpleUploadedFile("electric-kettle.jpg",b"demo-image",content_type="image/jpeg")
    client.post(f"/api/chat/sessions/{session['public_id']}/images/",{"image":image,"language":"en"},format="multipart")
    url=f"/api/chat/sessions/{session['public_id']}/messages/"

    stage=client.post(url,{"message":"ROADMAP_STAGE 07 OF 07\nSTAGE_TITLE: Set up production inspection and compliance records\nPRODUCT_CONTEXT: electric kettle","language":"en","silent":True},format="json")
    assert stage.status_code == 201
    assert stage.json()["intent"] == "roadmap_stage_detail"
    assert "Stage 7" in stage.json()["content"]
    assert stage.json()["next_steps"] == []

    lab=client.post(url,{"message":"Recommend a nearby BIS-recognized testing laboratory near Nagpur.\nProduct context: electric kettle\nStandard: IS 367:1993","language":"en","silent":True},format="json")
    assert lab.status_code == 201
    assert lab.json()["intent"] == "lab_locator"
    assert lab.json()["lab_results"]
    assert lab.json()["citations"][0]["standard_number"] == "IS 367:1993"

def test_session_detail_keeps_old_messages_and_hides_only_silent_prompts(client):
    session=client.post("/api/chat/sessions/",{"audience":"industry","language":"en"},format="json").json()
    url=f"/api/chat/sessions/{session['public_id']}/messages/"
    assert client.post(url,{"message":"electric kettle","language":"en"},format="json").status_code==201
    assert client.post(url,{"message":"near Nagpur","language":"en","silent":True},format="json").status_code==201
    messages=client.get(f"/api/chat/sessions/{session['public_id']}/").json()["messages"]
    assert any(item["content"]=="electric kettle" for item in messages)
    assert not any(item["content"]=="near Nagpur" for item in messages)
