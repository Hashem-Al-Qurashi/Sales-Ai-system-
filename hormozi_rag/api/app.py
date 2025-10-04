"""
Flask API for the Hormozi RAG system.

This module provides a REST API for testing and demonstrating
the framework retrieval capabilities.
"""

import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..config.settings import settings
from ..core.logger import get_logger
from ..core.orchestrator import RAGOrchestrator
from ..retrieval.retriever import HybridRetriever
from ..tests.test_framework_queries import run_validation_suite

logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=settings.api.cors_origins)

# Initialize rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=[settings.api.rate_limit]
)

# Global variables for retriever (loaded on startup)
retriever: Optional[HybridRetriever] = None
orchestrator: Optional[RAGOrchestrator] = None


@app.before_first_request
def initialize_system():
    """Initialize the RAG system on first request."""
    global retriever, orchestrator
    
    try:
        logger.info("Initializing RAG system for API")
        
        orchestrator = RAGOrchestrator()
        
        # Try to load processed data
        try:
            embedded_chunks = orchestrator.load_processed_data()
            retriever = HybridRetriever(embedded_chunks)
            logger.info("RAG system initialized successfully")
        except FileNotFoundError:
            logger.warning("No processed data found - API will have limited functionality")
            
    except Exception as e:
        logger.error("Failed to initialize RAG system", exception=e)


@app.route("/", methods=["GET"])
def home():
    """Home page with API documentation."""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hormozi RAG System API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 20px; }
            .section { margin: 30px 0; }
            .endpoint { background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }
            .method { font-weight: bold; color: #e74c3c; }
            .path { font-family: monospace; background: #ecf0f1; padding: 2px 5px; }
            .demo-query { background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 4px; }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .status.ready { background: #d4edda; color: #155724; }
            .status.warning { background: #fff3cd; color: #856404; }
            .status.error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 Hormozi RAG System API</h1>
            <p>Framework-aware retrieval for Alex Hormozi's $100M Offers</p>
        </div>
        
        <div class="section">
            <h2>System Status</h2>
            <div class="status {{ status_class }}">
                {{ status_message }}
            </div>
        </div>
        
        <div class="section">
            <h2>Core Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> <span class="path">/query</span>
                <p>Query the framework knowledge base</p>
                <p><strong>Body:</strong> <code>{"query": "What is the value equation?", "top_k": 5}</code></p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/frameworks</span>
                <p>List all available frameworks</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/framework/{name}</span>
                <p>Get complete framework by name</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <span class="path">/validate</span>
                <p>Run validation test suite</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/status</span>
                <p>Get system status and metrics</p>
            </div>
        </div>
        
        <div class="section">
            <h2>Demo Queries</h2>
            <p>These queries are designed to work perfectly for the Friday demo:</p>
            
            <div class="demo-query">
                <strong>Value Equation:</strong><br>
                "What's the value equation?" or "Explain the value equation formula"
            </div>
            
            <div class="demo-query">
                <strong>Offer Creation:</strong><br>
                "How do I create an irresistible offer for web design?"
            </div>
            
            <div class="demo-query">
                <strong>Guarantees:</strong><br>
                "Give me examples of guarantees for service businesses"
            </div>
            
            <div class="demo-query">
                <strong>Pricing:</strong><br>
                "How do I justify charging $10k instead of $5k?"
            </div>
        </div>
        
        <div class="section">
            <h2>Quick Test</h2>
            <p>Try a query directly in your browser:</p>
            <p><a href="/query?q=What is the value equation?" target="_blank">/query?q=What is the value equation?</a></p>
        </div>
    </body>
    </html>
    """
    
    # Determine system status
    if retriever is not None:
        status_class = "ready"
        status_message = "✅ System ready - RAG retrieval available"
    elif orchestrator is not None:
        status_class = "warning" 
        status_message = "⚠️ System partially ready - no processed data found"
    else:
        status_class = "error"
        status_message = "❌ System not initialized"
    
    return render_template_string(
        html_template,
        status_class=status_class,
        status_message=status_message
    )


@app.route("/query", methods=["POST", "GET"])
@limiter.limit("30 per minute")
def query():
    """Query the framework knowledge base."""
    
    if retriever is None:
        return jsonify({
            "error": "RAG system not initialized",
            "message": "No processed data available. Please run document processing first."
        }), 503
    
    try:
        # Handle both POST and GET requests
        if request.method == "POST":
            data = request.get_json()
            query_text = data.get("query", "")
            top_k = data.get("top_k", 5)
        else:
            query_text = request.args.get("q", "")
            top_k = int(request.args.get("top_k", 5))
        
        if not query_text:
            return jsonify({
                "error": "Missing query parameter",
                "message": "Please provide a 'query' parameter"
            }), 400
        
        # Validate top_k
        top_k = max(1, min(top_k, settings.api.max_response_chunks))
        
        # Perform retrieval
        start_time = datetime.now()
        results = retriever.retrieve(query_text, top_k=top_k)
        end_time = datetime.now()
        
        # Format response
        response = {
            "query": query_text,
            "results": [result.to_dict() for result in results],
            "metadata": {
                "total_results": len(results),
                "response_time_ms": int((end_time - start_time).total_seconds() * 1000),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if settings.api.include_sources:
            response["sources"] = list(set([
                r.chunk.source_file for r in results if r.chunk.source_file
            ]))
        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Query processing failed", exception=e, query=query_text)
        return jsonify({
            "error": "Query processing failed",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500


@app.route("/frameworks", methods=["GET"])
def list_frameworks():
    """List all available frameworks."""
    
    if retriever is None:
        return jsonify({
            "error": "RAG system not initialized"
        }), 503
    
    try:
        # Get unique frameworks
        frameworks = {}
        
        for chunk in retriever.chunks:
            if chunk.framework_name:
                if chunk.framework_name not in frameworks:
                    frameworks[chunk.framework_name] = {
                        "name": chunk.framework_name,
                        "priority": chunk.priority.value,
                        "chunks": 0,
                        "complete_framework_available": False,
                        "components": [],
                        "use_cases": set()
                    }
                
                framework_info = frameworks[chunk.framework_name]
                framework_info["chunks"] += 1
                framework_info["use_cases"].update(chunk.use_cases)
                
                if chunk.is_complete_framework:
                    framework_info["complete_framework_available"] = True
                
                if chunk.framework_component:
                    framework_info["components"].append(chunk.framework_component)
        
        # Convert sets to lists for JSON serialization
        for framework_info in frameworks.values():
            framework_info["use_cases"] = list(framework_info["use_cases"])
            framework_info["components"] = list(set(framework_info["components"]))
        
        return jsonify({
            "frameworks": list(frameworks.values()),
            "total_frameworks": len(frameworks)
        })
        
    except Exception as e:
        logger.error("Framework listing failed", exception=e)
        return jsonify({
            "error": "Framework listing failed",
            "message": str(e)
        }), 500


@app.route("/framework/<framework_name>", methods=["GET"])
def get_framework(framework_name: str):
    """Get complete framework by name."""
    
    if retriever is None:
        return jsonify({
            "error": "RAG system not initialized"
        }), 503
    
    try:
        results = retriever.get_framework(framework_name)
        
        if not results:
            return jsonify({
                "error": "Framework not found",
                "message": f"No framework found with name: {framework_name}"
            }), 404
        
        # Separate complete framework from components
        complete_framework = None
        components = []
        
        for result in results:
            if result.chunk.is_complete_framework:
                complete_framework = result.to_dict()
            else:
                components.append(result.to_dict())
        
        response = {
            "framework_name": framework_name,
            "complete_framework": complete_framework,
            "components": components,
            "total_chunks": len(results)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Framework retrieval failed", exception=e, framework=framework_name)
        return jsonify({
            "error": "Framework retrieval failed",
            "message": str(e)
        }), 500


@app.route("/validate", methods=["POST"])
def validate_system():
    """Run the validation test suite."""
    
    try:
        # Run validation suite
        start_time = datetime.now()
        results = run_validation_suite()
        end_time = datetime.now()
        
        results["validation_time"] = str(end_time - start_time)
        results["timestamp"] = datetime.now().isoformat()
        
        # Return appropriate status code
        status_code = 200 if results["success"] else 422
        
        return jsonify(results), status_code
        
    except Exception as e:
        logger.error("Validation failed", exception=e)
        return jsonify({
            "error": "Validation failed",
            "message": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500


@app.route("/status", methods=["GET"])
def system_status():
    """Get system status and metrics."""
    
    try:
        status = {
            "timestamp": datetime.now().isoformat(),
            "api_version": "1.0.0",
            "system_ready": retriever is not None,
            "orchestrator_ready": orchestrator is not None
        }
        
        if orchestrator:
            pipeline_status = orchestrator.get_pipeline_status()
            status.update(pipeline_status)
        
        if retriever:
            status.update({
                "total_chunks": len(retriever.chunks),
                "total_embeddings": len(retriever.embeddings),
                "frameworks_available": len(set(
                    c.framework_name for c in retriever.chunks 
                    if c.framework_name
                )),
                "retrieval_ready": True
            })
        else:
            status.update({
                "total_chunks": 0,
                "total_embeddings": 0, 
                "frameworks_available": 0,
                "retrieval_ready": False
            })
        
        return jsonify(status)
        
    except Exception as e:
        logger.error("Status check failed", exception=e)
        return jsonify({
            "error": "Status check failed",
            "message": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_ready": retriever is not None
    })


@app.route("/search", methods=["POST"])
@limiter.limit("20 per minute")
def search_by_use_case():
    """Search chunks by use case."""
    
    if retriever is None:
        return jsonify({
            "error": "RAG system not initialized"
        }), 503
    
    try:
        data = request.get_json()
        use_case = data.get("use_case", "")
        top_k = data.get("top_k", 10)
        
        if not use_case:
            return jsonify({
                "error": "Missing use_case parameter"
            }), 400
        
        results = retriever.search_by_use_case(use_case, top_k=top_k)
        
        return jsonify({
            "use_case": use_case,
            "results": [result.to_dict() for result in results],
            "total_results": len(results)
        })
        
    except Exception as e:
        logger.error("Use case search failed", exception=e)
        return jsonify({
            "error": "Use case search failed",
            "message": str(e)
        }), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors."""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later."
    }), 429


@app.errorhandler(404)
def not_found_handler(e):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist."
    }), 404


@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors."""
    logger.error("Internal server error", exception=e)
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred."
    }), 500


def create_app(test_config=None):
    """Application factory for testing."""
    if test_config:
        app.config.update(test_config)
    return app


if __name__ == "__main__":
    # Run the development server
    app.run(
        host=settings.api.host,
        port=settings.api.port,
        debug=settings.api.debug
    )