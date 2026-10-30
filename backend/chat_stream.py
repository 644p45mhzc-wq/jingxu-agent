"""Translate upstream chat streaming into small, safe browser events."""
import json
import httpx

def event(payload):
    return 'data: ' + json.dumps(payload, ensure_ascii=False) + '\n\n'

async def stream_reply(messages, key, model):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('POST', 'https://api.deepseek.com/chat/completions', headers={'Authorization':f'Bearer {key}'}, json={'model':model,'messages':messages,'stream':True,'max_tokens':6500}) as response:
                if response.status_code != 200:
                    errors={401:'DeepSeek 密钥无效。',402:'DeepSeek 账户余额不足。',429:'请求过于频繁，请稍后重试。'}
                    yield event({'error':errors.get(response.status_code,'AI 服务暂时不可用，请稍后重试。')})
                    return
                length=0
                finished=False
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    value=line[5:].strip()
                    if value=='[DONE]':
                        finished=True
                        break
                    packet=json.loads(value)
                    if not isinstance(packet, dict):
                        raise ValueError('Invalid stream packet')
                    if 'error' in packet:
                        yield event({'error':'AI 服务返回错误，请稍后重试。'})
                        return
                    choices=packet.get('choices',[])
                    if not isinstance(choices, list):
                        raise ValueError('Invalid stream choices')
                    if not choices:
                        continue
                    if not isinstance(choices[0], dict):
                        raise ValueError('Invalid stream choice')
                    delta = choices[0].get('delta', {})
                    if not isinstance(delta, dict):
                        raise ValueError('Invalid stream delta')
                    text = delta.get('content') or ''
                    if not isinstance(text, str):
                        raise ValueError('Invalid stream content')
                    if text:
                        length+=len(text)
                        if length>24000:
                            yield event({'error':'回复过长，请缩小问题范围后重试。'})
                            return
                        yield event({'delta':text})
                    reason=choices[0].get('finish_reason')
                    if reason and reason!='stop':
                        yield event({'error':'回复未完整生成，请缩小问题范围后重试。'})
                        return
                    finished=finished or reason=='stop'
                if not length or not finished:
                    yield event({'error':'回复未完整接收，请重试。'})
                else:
                    yield event({'done':True})
    except httpx.TimeoutException:
        yield event({'error':'AI 响应超时，请重试。'})
    except (httpx.RequestError, ValueError, TypeError, KeyError):
        yield event({'error':'AI 连接中断或返回格式异常，请重试。'})
