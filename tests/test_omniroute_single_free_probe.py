"""No-repeat zero-private-text one-request OmniRoute probe regression."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
import tempfile
from urllib import error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import omniroute_single_free_probe as probe
import ghost_omniroute_job as omni

class Reply:
    status=200
    def __init__(self, payload):
        self.payload=json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n): return self.payload[:n]

def catalog():
    models=omni.ROUTES["runner-blocker"][1]
    return [{"name":"rovor-fast-free-v1","strategy":"priority",
             "isHidden":False,
             "models":[{"kind":"model","providerId":"openrouter","model":m}
                       for m in models]}]

def state(circuit=True):
    return {"stop_requested":False,"database_status":"snapshot_readable",
            "inference_claim_guard_would_block":circuit}

class ProbeTests(unittest.TestCase):
    def test_default_and_unacknowledged_circuit_make_zero_model_requests(self):
        touched=[]
        extra={"read_status":lambda path:state(True),
               "read_catalog":lambda: touched.append("catalog"),
               "get_key":lambda: touched.append("key"),
               "open_local":lambda *a,**k: touched.append("HTTP")}
        result=probe.diagnose(**extra)
        self.assertEqual(result["request_count"],0)
        self.assertEqual(touched,[])
        result=probe.diagnose(approve_one_call=True, **extra)
        self.assertEqual(result["status"],"manual_acknowledgment_required_for_open_circuit")
        self.assertEqual(touched,[])

    def test_one_valid_response_does_not_log_answer_or_credentials(self):
        sent=[]
        def one(req,timeout):
            sent.append(req)
            self.assertEqual(req.full_url,"http://127.0.0.1:20128/v1/chat/completions")
            self.assertEqual(req.get_method(),"POST")
            self.assertEqual(timeout,75)
            data=json.loads(req.data)
            self.assertEqual(data["model"],"rovor-fast-free-v1")
            self.assertEqual(data["max_tokens"],512)
            self.assertNotIn("reasoning",data)
            self.assertNotIn("PRIVATE_PROJECT",json.dumps(data))
            return Reply({"choices":[{"message":{"content":"READY"},
                                      "finish_reason":"stop"}],
                          "usage":{"prompt_tokens":12,"completion_tokens":2,
                                   "completion_tokens_details":{"reasoning_tokens":0},
                                   "private_details":"SECRET"}})
        response=probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:state(),
            read_catalog=catalog,
            get_key=lambda:"secret-api-key",
            open_local=one)
        self.assertEqual(len(sent),1)
        self.assertEqual(response["status"],"completed_visible_ready")
        self.assertTrue(response["model_output_verified"])
        self.assertEqual(response["usage"]["reasoning_tokens"],0)
        self.assertNotIn("SECRET",json.dumps(response))
        self.assertEqual(response["request_count"],1)

    def test_real_mac_counter_mismatch_can_admit_one_valid_visible_response(self):
        calls=[]
        def one(req, timeout):
            calls.append(req)
            return Reply({"choices":[{"message":{"content":"READY"},
                                      "finish_reason":"stop"}],
                          "usage":{"prompt_tokens":27,"completion_tokens":52,
                                   "total_tokens":79,
                                   "completion_tokens_details":{"reasoning_tokens":59}}})
        result=probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:state(),read_catalog=catalog,
            get_key=lambda:"credential-hidden",open_local=one)
        self.assertEqual(len(calls),1)
        self.assertEqual(result["request_count"],1)
        self.assertEqual(result["status"],"completed_visible_ready")
        self.assertTrue(result["model_output_verified"])
        self.assertEqual(result["usage"]["reasoning_tokens"],59)
        self.assertNotIn("credential-hidden",json.dumps(result))

    def test_real_mac_counter_mismatch_does_not_admit_truncated_response(self):
        calls=[]
        def one(req, timeout):
            calls.append(req)
            return Reply({"choices":[{"message":{"content":"Partial"},
                                      "finish_reason":"length"}],
                          "usage":{"prompt_tokens":27,"completion_tokens":52,
                                   "total_tokens":79,
                                   "completion_tokens_details":{"reasoning_tokens":59}}})
        result=probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:state(),read_catalog=catalog,
            get_key=lambda:"hidden",open_local=one)
        self.assertEqual(result["status"],"admission_incomplete_length_stop")
        self.assertEqual(result["request_count"],1)
        self.assertEqual(len(calls),1)
        self.assertFalse(result["model_output_verified"])

    def test_exhausted_reasoning_is_classified_and_not_retried(self):
        count=[]
        def one(req,timeout):
            count.append(1)
            return Reply({"choices":[{"message":{"content":""},
                         "finish_reason":"length"}],
                         "usage":{"completion_tokens":512,
                                  "completion_tokens_details":{"reasoning_tokens":512}}})
        result=probe.diagnose(
            approve_one_call=True, acknowledge_open_circuit=True,
            read_status=lambda path:state(),read_catalog=catalog,
            get_key=lambda:"secret",open_local=one)
        self.assertEqual(result["status"],"admission_reasoning_budget_exhausted")
        self.assertEqual(result["request_count"],1)
        self.assertEqual(len(count),1)
        self.assertFalse(result["model_output_verified"])

    def test_unapproved_or_changed_route_never_calls_gateway(self):
        touched=[]
        result=probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:state(),
            read_catalog=lambda:[{"name":"rovor-fast-free-v1",
                "strategy":"priority","isHidden":False,"models":[]}],
            get_key=lambda: touched.append("SECRET"),open_local=lambda *a,**k:None)
        self.assertEqual(result["status"],"free_combo_missing_or_changed")
        self.assertEqual(touched,[])
        self.assertEqual(result["request_count"],0)

    def test_stop_never_sends_gateway_request(self):
        s=state()
        s["stop_requested"]=True
        self.assertEqual(probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:s)["status"],"owner_stop_or_status_unknown")

    def test_stop_arriving_after_preflight_blocks_the_only_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder)
            touches = []
            def auth():
                (local / "STOP").write_text("owner control")
                return "secret"
            with mock.patch.object(probe, "STATE", local):
                result=probe.diagnose(
                    approve_one_call=True, acknowledge_open_circuit=True,
                    read_status=lambda path:state(), read_catalog=catalog,
                    get_key=auth, open_local=lambda *a,**k:touches.append("bad"))
            self.assertEqual(result["status"],"owner_stop_requested_before_probe")
            self.assertEqual(result["request_count"],0)
            self.assertEqual(touches,[])

    def test_http_error_hides_raw_message_and_never_retries(self):
        calls=[]
        def failed(req,timeout):
            calls.append(1)
            raise error.HTTPError("http://127.0.0.1:20128", 429,
                                  "PRIVATE_UPSTREAM_TEXT",None,None)
        result=probe.diagnose(
            approve_one_call=True,acknowledge_open_circuit=True,
            read_status=lambda path:state(),read_catalog=catalog,
            get_key=lambda:"secret",open_local=failed)
        self.assertEqual(result["status"],"http_429")
        self.assertEqual(len(calls),1)
        self.assertNotIn("PRIVATE_UPSTREAM_TEXT",json.dumps(result))

if __name__ == "__main__":
    unittest.main()
