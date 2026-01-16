"""
基于智谱AI API的新闻媒体仿真API服务器
支持媒体提问和用户评论生成
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import json
import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
import logging
from dotenv import load_dotenv
from prompts.templates import get_media_prompt, get_user_prompt
THINKING_ENABLED = False
# 导入智谱AI SDK
try:
    from zhipuai import ZhipuAI
except ImportError:
    print("请安装智谱AI SDK: pip install zhipuai")
    raise

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="新闻媒体仿真API（智谱AI版）",
    description="基于智谱AI GLM-4.5的媒体提问和用户评论生成API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置智谱AI客户端
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY")
if not ZHIPU_API_KEY:
    logger.error("未找到ZHIPUAI_API_KEY环境变量，请在.env文件中配置")
    raise ValueError("ZHIPUAI_API_KEY环境变量未设置")

# 模型配置
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4.5-flash")  # 可配置模型
THINKING_ENABLED = os.getenv("THINKING_ENABLED", "false").lower() == "true"
STREAM_ENABLED = os.getenv("STREAM_ENABLED", "false").lower() == "true"

# 初始化客户端
try:
    client = ZhipuAI(api_key=ZHIPU_API_KEY)
    logger.info(f"智谱AI客户端初始化成功，使用模型: {MODEL_NAME}")
except Exception as e:
    logger.error(f"智谱AI客户端初始化失败: {str(e)}")
    raise

# 数据模型
class AgentRequest(BaseModel):
    agent_type: str  # "media" or "user"
    agent_id: str
    topic: str
    attributes: Optional[Dict] = {}
    context: str = ""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = None  # 是否启用流式输出

class BatchRequest(BaseModel):
    requests: List[AgentRequest]

class MediaProfileRequest(BaseModel):
    media_ids: Optional[List[str]] = None

class StreamRequest(BaseModel):
    agent_type: str
    agent_id: str
    topic: str
    attributes: Optional[Dict] = {}
    context: str = ""

# 加载智能体数据
def load_agent_data():
    """加载媒体和用户数据"""
    try:
        # 加载媒体数据
        media_path = 'agents_data/media_profiles.json'
        if os.path.exists(media_path):
            with open(media_path, 'r', encoding='utf-8') as f:
                media_data = json.load(f)
            logger.info(f"已加载 {len(media_data)} 个媒体档案")
        else:
            logger.warning(f"媒体数据文件不存在: {media_path}")
            media_data = {}
        
        # 加载用户数据
        user_path = 'agents_data/user_profiles.json'
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            logger.info(f"已加载 {len(user_data)} 个用户档案")
        else:
            logger.warning("用户数据文件不存在，使用空数据")
            user_data = {}
            
        return media_data, user_data
    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        raise

# 全局数据变量
media_profiles, user_profiles = load_agent_data()

# 辅助函数
def find_media_by_id_or_name(identifier: str) -> Optional[Dict]:
    """根据ID或名称查找媒体"""
    # 直接匹配ID
    if identifier in media_profiles:
        return media_profiles[identifier]
    
    # 尝试模糊匹配（去除特殊字符，不区分大小写）
    clean_identifier = identifier.lower().replace('《', '').replace('》', '').replace(' ', '')
    
    for media_id, profile in media_profiles.items():
        basic_info = profile.get("basic_info", {})
        media_name = basic_info.get("name", "")
        
        # 清理媒体名称
        clean_name = media_name.lower().replace('《', '').replace('》', '').replace(' ', '')
        
        if clean_identifier in clean_name or clean_name in clean_identifier:
            return profile
        
        # 检查媒体ID
        if clean_identifier in media_id.lower():
            return profile
    
    return None

# 修改 api_server.py 中的 generate_with_zhipuai 函数

async def generate_with_zhipuai(messages: List[Dict], temperature: float = 0.7, 
                               max_tokens: int = 300, stream: bool = False) -> Dict:
    """调用智谱AI API生成内容"""
    try:
        # 配置思考模式
        thinking_config = {"type": "enabled"} if THINKING_ENABLED else {}
        
        # 构建请求参数
        params = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream or STREAM_ENABLED
        }
        
        # 如果有思考模式配置，添加到参数中
        if thinking_config:
            params["thinking"] = thinking_config
        
        logger.info(f"调用智谱AI API，模型: {MODEL_NAME}, 温度: {temperature}, 流式: {stream}")
        logger.debug(f"消息: {messages}")
        
        # 调用API
        response = client.chat.completions.create(**params)
        try:
            # 使用 model_dump 获取完整数据
            if hasattr(response, 'model_dump'):
                data = response.model_dump()
                
                if 'choices' in data and data['choices']:
                    choice = data['choices'][0]
                    if 'message' in choice and isinstance(choice['message'], dict):
                        message = choice['message']
                        
                        # 优先获取 content
                        content = message.get('content', '')
                        
                        # 如果 content 为空，尝试获取 reasoning_content
                        if not content and 'reasoning_content' in message:
                            reasoning = message['reasoning_content']
                            # 从推理内容中提取最终答案
                            if reasoning:
                                # 尝试找到类似最终答案的部分
                                lines = reasoning.split('\n')
                                for line in reversed(lines):  # 从最后往前找
                                    line = line.strip()
                                    if line and len(line) > 10 and not line.startswith('我需要') and not line.startswith('作为一个'):
                                        return line
                                
                                # 如果没有明显答案，返回最后一段推理
                                return reasoning[-200:] if len(reasoning) > 200 else reasoning
                        
                        return content
            
            return ""
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return ""
        
    except Exception as e:
        logger.error(f"智谱AI API调用失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI API调用失败: {str(e)}")
    
    
    
async def stream_response_generator(stream_response) -> AsyncGenerator[str, None]:
    """生成流式响应"""
    try:
        for chunk in stream_response:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
    except Exception as e:
        logger.error(f"流式响应生成失败: {str(e)}")
        yield f"错误: {str(e)}"

# API端点
@app.get("/")
async def root():
    """API根端点"""
    return {
        "service": "News Media Simulation API (ZhipuAI)",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "streaming_enabled": STREAM_ENABLED,
        "thinking_enabled": THINKING_ENABLED,
        "endpoints": {
            "媒体数据": "/media/{media_id}",
            "所有媒体": "/media",
            "用户数据": "/user/{user_id}",
            "生成内容": "/generate",
            "流式生成": "/stream-generate",
            "批量生成": "/batch-generate",
            "模拟发布会": "/simulate-press-conference"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": os.times().elapsed,
        "model": MODEL_NAME,
        "media_count": len(media_profiles),
        "user_count": len(user_profiles)
    }

@app.get("/media/{media_id}")
async def get_media_profile(media_id: str):
    """获取媒体详细信息"""
    try:
        profile = find_media_by_id_or_name(media_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"媒体 '{media_id}' 不存在")
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取媒体信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/media")
async def get_all_media():
    """获取所有媒体列表（简略信息）"""
    try:
        result = []
        for media_id, profile in media_profiles.items():
            basic_info = profile.get("basic_info", {})
            taiwan_analysis = profile.get("taiwan_issue_analysis", {})
            generation_params = profile.get("generation_parameters", {})
            
            media_info = {
                "id": media_id,
                "name": basic_info.get("name", "未知"),
                "country": basic_info.get("country", "未知"),
                "media_type": basic_info.get("media_type", "未知"),
                "ownership": basic_info.get("ownership", "未知"),
                "stance_label": taiwan_analysis.get("stance_label", "未知"),
                "total_questions": taiwan_analysis.get("total_questions", 0),
                "counter_ratio": taiwan_analysis.get("counter_ratio", 0),
                "aligned_ratio": taiwan_analysis.get("aligned_ratio", 0),
                "question_style": generation_params.get("question_style", "未知")
            }
            result.append(media_info)
        
        return {
            "count": len(result),
            "media": result
        }
    except Exception as e:
        logger.error(f"获取媒体列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    """获取用户信息"""
    try:
        if user_id not in user_profiles:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user_profiles[user_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate_content(request: AgentRequest):
    """根据智能体属性生成内容（非流式）"""
    try:
        logger.info(f"生成请求: {request.agent_type} - {request.agent_id} - {request.topic}")
        
        # 获取智能体属性
        if request.agent_type == "media":
            profile = find_media_by_id_or_name(request.agent_id)
            if not profile:
                raise HTTPException(status_code=404, detail=f"媒体 '{request.agent_id}' 不存在")
            
            merged_attributes = {**profile, **request.attributes}
            
            # 获取媒体提问的提示词
            prompt = get_media_prompt(
                topic=request.topic,
                attributes=merged_attributes,
                context=request.context
            )
            logger.info(f"媒体提示词: {prompt}")
            
        elif request.agent_type == "user":
            if request.agent_id not in user_profiles:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            profile = user_profiles[request.agent_id]
            merged_attributes = {**profile, **request.attributes}
            
            # 获取用户评论的提示词
            prompt = get_user_prompt(
                topic=request.topic,
                attributes=merged_attributes,
                context=request.context
            )
        else:
            raise HTTPException(status_code=400, detail="agent_type 必须是 'media' 或 'user'")
        
        # 准备生成参数
        temperature = request.temperature if request.temperature is not None else 0.7
        max_tokens = request.max_tokens if request.max_tokens is not None else 300
        stream = request.stream if request.stream is not None else False
        
        # 构建消息
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": prompt}
        ]
        logger.info(f"消息: {messages}")
        
        # 调用智谱AI API
        response = await generate_with_zhipuai(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        # 处理响应
        if stream:
            # 流式响应 - 收集所有内容
            content_parts = []
            async for chunk in stream_response_generator(response):
                content_parts.append(chunk)
            generated_text = "".join(content_parts)
        else:
            # 非流式响应
            if hasattr(response, 'choices') and response.choices:
                generated_text = response.choices[0].message.reasoning_content
            else:
                raise HTTPException(status_code=500, detail="AI API返回格式异常")
        
        # 获取使用情况
        usage = {}
        if hasattr(response, 'usage'):
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        result = {
            "agent_id": request.agent_id,
            "agent_type": request.agent_type,
            "content": generated_text.strip(),
            "metadata": {
                "model": MODEL_NAME,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                "tokens_used": usage,
                "prompt_length": len(prompt)
            }
        }
        
        logger.info(f"生成成功: {result['agent_type']} - {result['agent_id']} - 长度: {len(generated_text)}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

@app.post("/stream-generate")
async def stream_generate_content(request: StreamRequest):
    """流式生成内容（Server-Sent Events）"""
    try:
        logger.info(f"流式生成请求: {request.agent_type} - {request.agent_id} - {request.topic}")
        
        # 获取智能体属性
        if request.agent_type == "media":
            profile = find_media_by_id_or_name(request.agent_id)
            if not profile:
                raise HTTPException(status_code=404, detail=f"媒体 '{request.agent_id}' 不存在")
            
            merged_attributes = {**profile, **request.attributes}
            
            # 获取媒体提问的提示词
            prompt = get_media_prompt(
                topic=request.topic,
                attributes=merged_attributes,
                context=request.context
            )
            logger.info(f"媒体提示词: {prompt}")
            
        elif request.agent_type == "user":
            if request.agent_id not in user_profiles:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            profile = user_profiles[request.agent_id]
            merged_attributes = {**profile, **request.attributes}
            
            # 获取用户评论的提示词
            prompt = get_user_prompt(
                topic=request.topic,
                attributes=merged_attributes,
                context=request.context
            )
        else:
            raise HTTPException(status_code=400, detail="agent_type 必须是 'media' 或 'user'")
        
        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的新闻仿真生成器"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用智谱AI API（流式）
        response = await generate_with_zhipuai(
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            stream=True
        )
        
        # 返回流式响应
        async def event_generator():
            try:
                # 发送开始事件
                yield f"data: {json.dumps({'event': 'start', 'agent_id': request.agent_id, 'agent_type': request.agent_type})}\n\n"
                
                # 发送内容流
                async for chunk in stream_response_generator(response):
                    if chunk:
                        yield f"data: {json.dumps({'event': 'content', 'chunk': chunk})}\n\n"
                
                # 发送结束事件
                yield f"data: {json.dumps({'event': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"流式生成过程中出错: {str(e)}")
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
            }
        )
        
    except Exception as e:
        logger.error(f"流式生成失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"流式生成失败: {str(e)}"}
        )

@app.post("/batch-generate")
async def batch_generate_content(batch_request: BatchRequest):
    """批量生成内容"""
    try:
        results = []
        errors = []
        
        for req in batch_request.requests:
            try:
                # 构建单个请求
                agent_request = AgentRequest(
                    agent_type=req.agent_type,
                    agent_id=req.agent_id,
                    topic=req.topic,
                    attributes=req.attributes,
                    context=req.context,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    stream=False  # 批量请求不使用流式
                )
                
                result = await generate_content(agent_request)
                results.append(result)
                
            except Exception as e:
                errors.append({
                    "agent_id": req.agent_id,
                    "agent_type": req.agent_type,
                    "error": str(e)
                })
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"批量生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate-press-conference")
async def simulate_press_conference(request: dict):
    """模拟新闻发布会"""
    try:
        topic = request.get("topic", "")
        media_ids = request.get("media_ids", [])
        context = request.get("context", "")
        stream = request.get("stream", False)
        
        if not topic:
            raise HTTPException(status_code=400, detail="需要提供议题")
        
        if not media_ids:
            # 如果没有指定媒体，使用前5个Aligned媒体和前2个非Aligned媒体
            aligned_medias = []
            other_medias = []
            
            for media_id, profile in media_profiles.items():
                taiwan_analysis = profile.get("taiwan_issue_analysis", {})
                if taiwan_analysis.get("stance_label") == "Aligned":
                    aligned_medias.append(media_id)
                else:
                    other_medias.append(media_id)
            
            media_ids = aligned_medias[:5] + other_medias[:2]
        
        if stream:
            # 流式模拟发布会
            async def conference_stream_generator():
                yield f"data: {json.dumps({'event': 'start', 'topic': topic, 'total_media': len(media_ids)})}\n\n"
                
                for i, media_id in enumerate(media_ids):
                    if media_id in media_profiles:
                        try:
                            # 获取媒体信息
                            profile = media_profiles[media_id]
                            basic_info = profile.get("basic_info", {})
                            
                            yield f"data: {json.dumps({'event': 'media_start', 'media_id': media_id, 'media_name': basic_info.get('name', media_id), 'index': i})}\n\n"
                            
                            # 生成问题
                            agent_request = AgentRequest(
                                agent_type="media",
                                agent_id=media_id,
                                topic=topic,
                                context=context,
                                temperature=0.7,
                                max_tokens=200,
                                stream=False
                            )
                            
                            result = await generate_content(agent_request)
                            content = result.get("content", "")
                            
                            yield f"data: {json.dumps({'event': 'question', 'media_id': media_id, 'question': content})}\n\n"
                            yield f"data: {json.dumps({'event': 'media_end', 'media_id': media_id})}\n\n"
                            
                            # 等待间隔（模拟真实发布会）
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            logger.warning(f"媒体 {media_id} 生成问题失败: {str(e)}")
                            yield f"data: {json.dumps({'event': 'error', 'media_id': media_id, 'message': str(e)})}\n\n"
                
                yield f"data: {json.dumps({'event': 'end', 'message': '新闻发布会结束'})}\n\n"
            
            return StreamingResponse(
                conference_stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        else:
            # 非流式模拟发布会
            questions = []
            for media_id in media_ids:
                if media_id in media_profiles:
                    try:
                        agent_request = AgentRequest(
                            agent_type="media",
                            agent_id=media_id,
                            topic=topic,
                            context=context,
                            temperature=0.7,
                            max_tokens=200,
                            stream=False
                        )
                        
                        result = await generate_content(agent_request)
                        questions.append(result)
                        
                    except Exception as e:
                        logger.warning(f"媒体 {media_id} 生成问题失败: {str(e)}")
                        questions.append({
                            "agent_id": media_id,
                            "error": str(e),
                            "content": ""
                        })
            
            return {
                "topic": topic,
                "context": context,
                "total_media": len(questions),
                "questions": questions
            }
        
    except Exception as e:
        logger.error(f"模拟发布会失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_api_stats():
    """获取API统计信息"""
    return {
        "media_count": len(media_profiles),
        "user_count": len(user_profiles),
        "model": MODEL_NAME,
        "thinking_enabled": THINKING_ENABLED,
        "streaming_enabled": STREAM_ENABLED,
        "supported_models": ["glm-4.5-flash", "glm-4", "glm-3-turbo"],
        "current_timestamp": os.times().elapsed
    }

@app.get("/model-info")
async def get_model_info():
    """获取模型信息"""
    return {
        "model": MODEL_NAME,
        "provider": "ZhipuAI",
        "capabilities": ["chat-completion", "streaming", "thinking"],
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_thinking": True
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": f"内部服务器错误: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"启动API服务器，地址: {host}:{port}")
    logger.info(f"使用模型: {MODEL_NAME}")
    logger.info(f"流式输出: {STREAM_ENABLED}")
    logger.info(f"思考模式: {THINKING_ENABLED}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )