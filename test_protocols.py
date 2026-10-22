"""Binary protocol and device safety regression tests (no real hardware needed)."""
import asyncio
import struct
from types import SimpleNamespace

import pytest

from custom_components.power_manager.protocols import (
    TransportError,
    encode_modbus_registers,
    build_modbus_request,
    validate_modbus_response,
    async_modbus_write,
    async_mqtt_publish,
)
from custom_components.power_manager.outputs import (
    build_output_plan, OutputConversionError,
)
from custom_components.power_manager.load_config import validate_load_data


@pytest.mark.parametrize("order,expected", [
    ("ABCD", (0x4120, 0x0000)),
    ("BADC", (0x2041, 0x0000)),
    ("CDAB", (0x0000, 0x4120)),
    ("DCBA", (0x0000, 0x2041)),
])
def test_float32_has_correct_modbus_register_byte_order(order, expected):
    assert encode_modbus_registers(10.0, "float32", order) == expected


def test_fc16_writes_two_registers_with_valid_mbap():
    msg=build_modbus_request(
        transaction=7,unit_id=6,address=770,
        values=encode_modbus_registers(10.0,"float32","ABCD"),
    )
    assert struct.unpack(">HHHB", msg[:7]) == (7,0,11,6)
    assert struct.unpack(">BHHB", msg[7:13]) == (16,770,2,4)
    assert msg[13:] == bytes((0x41, 0x20, 0, 0))
    response=struct.pack(">HHHB",7,0,6,6)+struct.pack(">BHH",16,770,2)
    validate_modbus_response(msg,response)


def test_fc06_rejects_two_register_float32():
    with pytest.raises(TransportError):
        build_modbus_request(transaction=1,unit_id=6,address=770,
                             values=(1,2),function=6)


@pytest.mark.parametrize("data,value",[
    ("uint16",-1),("int16",70000),("uint16",1.25),
    ("float32",float("nan")),("uint32",-3),
])
def test_invalid_numeric_register_content_cannot_be_sent(data,value):
    with pytest.raises(TransportError):
        encode_modbus_registers(value,data,"ABCD")


def test_bad_modbus_ack_is_not_silently_accepted():
    req=build_modbus_request(transaction=5,unit_id=6,address=770,values=(0x4120,0))
    bad=struct.pack(">HHHB",5,0,6,6)+struct.pack(">BHH",16,771,2)
    with pytest.raises(TransportError, match="mismatch"):
        validate_modbus_response(req,bad)


def test_modbus_exception_reply_causes_error():
    req=build_modbus_request(transaction=5,unit_id=6,address=770,values=(0x4120,0))
    bad=struct.pack(">HHHB",5,0,3,6)+bytes((0x90,2))
    with pytest.raises(TransportError, match="exception"):
        validate_modbus_response(req,bad)


def test_direct_modbus_tcp_roundtrip_against_fake_server():
    async def run():
        observed=[]
        async def server(reader,writer):
            hdr=await reader.readexactly(7)
            length=struct.unpack(">H",hdr[4:6])[0]
            body=await reader.readexactly(length-1)
            observed.append(hdr+body)
            writer.write(
                struct.pack(">HHHB",1,0,6,6)
                +struct.pack(">BHH",16,770,2)
            )
            await writer.drain()
            writer.close()
        srv=await asyncio.start_server(server,"127.0.0.1",0)
        try:
            port=srv.sockets[0].getsockname()[1]
            await async_modbus_write(
                host="127.0.0.1",port=port,unit_id=6,address=770,
                value=10,data_type="float32",byte_order="ABCD",
                function=16,timeout_s=2,
            )
        finally:
            srv.close()
            await srv.wait_closed()
        assert len(observed)==1
        assert observed[0][7:13]==struct.pack(">BHHB",16,770,2,4)
    asyncio.run(run())


def test_mqtt_payload_uses_only_safe_numeric_value_and_configured_topic():
    class Services:
        def __init__(self):
            self.calls=[]
        def has_service(self,d,s):return (d,s)==("mqtt","publish")
        async def async_call(self,d,s,p,blocking=False):
            self.calls.append((d,s,p,blocking))
    services=Services()
    async def run():
        await async_mqtt_publish(
            SimpleNamespace(services=services),topic="evse/1/set",
            value=6.0,template='{"amperes":{value}}',
            qos=1,retain=False,
        )
    asyncio.run(run())
    assert services.calls[0][2]["payload"]=='{"amperes":6}'
    assert services.calls[0][2]["retain"] is False


def test_mqtt_missing_publish_service_fails_closed():
    class Services:
        def has_service(self,*args):return False
    async def run():
        with pytest.raises(TransportError,match="unavailable"):
            await async_mqtt_publish(
                SimpleNamespace(services=Services()),topic="wallbox/current",
                value=6.0,template="{value}",qos=0,retain=False,
            )
    asyncio.run(run())


def test_discrete_numeric_output_selects_safe_stage_below_target():
    mapping='[{"kw":4.14,"code":6},{"kw":6.9,"code":10},{"kw":11.04,"code":16}]'
    kw=lambda value: build_output_plan(
        load_type="modulating",target_kw=value,output_value_mode="steps",
        output_steps_json=mapping,safe_output_value=0.01,forbidden_value=0,
    )
    assert kw(0).numeric_value==pytest.approx(0.01)
    assert kw(3).enabled is False
    assert kw(4.14).numeric_value==6
    assert kw(7).numeric_value==10
    assert kw(11.04).numeric_value==16


def test_stage_profile_rejects_invalid_codes_and_unsafe_pause():
    with pytest.raises(OutputConversionError):
        build_output_plan(
            load_type="modulating",target_kw=5,output_value_mode="steps",
            output_steps_json='[{"kw":5,"code":0}]',
            forbidden_value=0,
        )


def test_direct_command_requires_operator_safety_acknowledgement():
    data=dict(load_name="Device",load_type="modulating",priority=1,
              min_kw=1,max_kw=5,output_transport="modbus_tcp",
              modbus_host="127.0.0.1",modbus_register=770,
              output_unit="kW",device_commands_confirmed=False)
    errors=validate_load_data(data)
    assert errors["device_commands_confirmed"]=="unsafe_command_unconfirmed"
    data["device_commands_confirmed"]=True
    assert "device_commands_confirmed" not in validate_load_data(data)


def test_direct_modbus_wrong_function_is_blocked():
    data=dict(load_name="Device",load_type="modulating",priority=1,
              min_kw=1,max_kw=5,output_transport="modbus_tcp",
              modbus_host="127.0.0.1",modbus_register=770,
              output_unit="kW",device_commands_confirmed=True,
              modbus_data_type="float32",modbus_function=6)
    assert "modbus_function" in validate_load_data(data)


def test_modbus_valid_ipv4_host_not_rejected_by_literal_escape_characters():
    data=dict(load_name="Host",load_type="modulating",priority=1,
              min_kw=1,max_kw=5,output_transport="modbus_tcp",
              modbus_host="192.168.0.15",modbus_register=770,
              output_unit="kW",device_commands_confirmed=True)
    err=validate_load_data(data)
    assert "modbus_host" not in err, err


def test_mqtt_valid_topic_can_contain_n_and_zero():
    data=dict(load_name="MQTT",load_type="modulating",priority=1,
              min_kw=1,max_kw=5,output_transport="mqtt",
              mqtt_topic="home/zone0/energy",output_unit="kW",
              device_commands_confirmed=True)
    err=validate_load_data(data)
    assert "mqtt_topic" not in err, err


def test_modbus_host_path_delimiter_rejected():
    data=dict(load_name="Invalid",load_type="modulating",priority=1,
              min_kw=1,max_kw=5,output_transport="modbus_tcp",
              modbus_host="10.0.0.1/bad",modbus_register=770,
              output_unit="kW",device_commands_confirmed=True)
    assert "modbus_host" in validate_load_data(data)


def test_mqtt_enum_switch_payload_validation():
    data = dict(
        load_name="Switch", load_type="switch", priority=1, min_kw=3,
        max_kw=3, output_transport="mqtt", mqtt_topic="plant/switch",
        mqtt_on_payload="ENABLE", mqtt_off_payload="DISABLE",
        device_commands_confirmed=True,
    )
    assert "mqtt_on_payload" not in validate_load_data(data)
    broken = dict(data, mqtt_off_payload="")
    assert "mqtt_on_payload" in validate_load_data(broken)
    broken = dict(data, load_type="modulating")
    assert "mqtt_on_payload" in validate_load_data(broken)


def test_mqtt_enum_switch_publishes_safe_text_without_numeric_cast():
    import asyncio
    from custom_components.power_manager.protocols import async_mqtt_publish
    calls = []
    class Services:
        def has_service(self, domain, service):
            return domain == "mqtt" and service == "publish"
        async def async_call(self, domain, service, payload, blocking):
            calls.append((domain, service, payload, blocking))
    class HA:
        services = Services()
    asyncio.run(async_mqtt_publish(
        HA(), topic="device/control", value=0,
        template="{value}", qos=0, retain=False,
        payload_override="DISABLE",
    ))
    assert calls[0][2]["payload"] == "DISABLE"
