"""
Ollama Client Wrapper - Multi-Node Support
Handles interaction with Qwen 3 235B MoE across 2× DGX Spark nodes
Intelligent load balancing for 2× inference speed
"""
import ollama
import random
import time
from backend.config import Config

class OllamaClient:
    """Multi-node Ollama wrapper with load balancing"""
    
    def __init__(self, model=None, nodes=None):
        self.model = model or Config.OLLAMA_MODEL
        
        # Multi-node configuration
        if nodes:
            self.nodes = nodes
        else:
            # Default: try multi-node if configured, fallback to single
            primary = Config.OLLAMA_HOST
            self.nodes = [primary]
            
            # Check if multi-node is configured
            if hasattr(Config, 'OLLAMA_NODES') and Config.OLLAMA_NODES:
                self.nodes = Config.OLLAMA_NODES
        
        self.clients = [ollama.Client(host=node) for node in self.nodes]
        self.current_node_idx = 0
        
        print(f"🧠 Ollama multi-node initialized:")
        for i, node in enumerate(self.nodes):
            print(f"   Node {i+1}: {node}")
    
    def _get_next_client(self):
        """Round-robin load balancing across nodes"""
        client = self.clients[self.current_node_idx]
        node = self.nodes[self.current_node_idx]
        
        # Rotate to next node for next request
        self.current_node_idx = (self.current_node_idx + 1) % len(self.clients)
        
        return client, node
    
    def _get_random_client(self):
        """Random node selection (alternative strategy)"""
        idx = random.randint(0, len(self.clients) - 1)
        return self.clients[idx], self.nodes[idx]
    
    def chat(self, messages, stream=True, use_node=None):
        """
        Send chat messages to Ollama with multi-node support
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Boolean, whether to stream response
            use_node: Optional specific node index to use (0 or 1)
            
        Yields:
            Chunks of response text if stream=True
            Returns full response if stream=False
        """
        # Select node
        if use_node is not None and 0 <= use_node < len(self.clients):
            client = self.clients[use_node]
            node = self.nodes[use_node]
        else:
            client, node = self._get_next_client()
        
        try:
            start_time = time.time()
            print(f"🔄 Routing to {node} | Model: {self.model}")
            
            response = client.chat(
                model=self.model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                for chunk in response:
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
                
                elapsed = time.time() - start_time
                print(f"✓ Response completed in {elapsed:.2f}s from {node}")
            else:
                result = response['message']['content']
                elapsed = time.time() - start_time
                print(f"✓ Response completed in {elapsed:.2f}s from {node}")
                return result
                
        except Exception as e:
            print(f"❌ Ollama error on {node}: {str(e)}")
            
            # Fallback: try other node if available
            if len(self.clients) > 1:
                print(f"🔄 Failing over to alternate node...")
                other_idx = (self.current_node_idx) % len(self.clients)
                client = self.clients[other_idx]
                node = self.nodes[other_idx]
                
                try:
                    response = client.chat(
                        model=self.model,
                        messages=messages,
                        stream=stream
                    )
                    
                    if stream:
                        for chunk in response:
                            if 'message' in chunk and 'content' in chunk['message']:
                                yield chunk['message']['content']
                    else:
                        return response['message']['content']
                except Exception as e2:
                    print(f"❌ Failover also failed: {str(e2)}")
                    raise
            else:
                raise
    
    def generate(self, prompt, stream=True, use_node=None):
        """
        Generate completion from prompt
        
        Args:
            prompt: String prompt
            stream: Boolean, whether to stream response
            use_node: Optional specific node index
            
        Yields:
            Chunks of response text if stream=True
            Returns full response if stream=False
        """
        # Select node
        if use_node is not None and 0 <= use_node < len(self.clients):
            client = self.clients[use_node]
            node = self.nodes[use_node]
        else:
            client, node = self._get_next_client()
        
        try:
            print(f"🔄 Routing to {node}")
            
            response = client.generate(
                model=self.model,
                prompt=prompt,
                stream=stream
            )
            
            if stream:
                for chunk in response:
                    if 'response' in chunk:
                        yield chunk['response']
            else:
                return response['response']
                
        except Exception as e:
            print(f"❌ Ollama generate error on {node}: {str(e)}")
            raise
    
    def health_check(self):
        """Check health of all nodes"""
        results = []
        
        for i, (client, node) in enumerate(zip(self.clients, self.nodes)):
            try:
                models = client.list()
                model_names = [m['name'] for m in models.get('models', [])]
                
                if self.model in model_names:
                    results.append(f"✓ Node {i+1} ({node}): {self.model} ready")
                else:
                    results.append(f"✗ Node {i+1} ({node}): Model not found")
            except Exception as e:
                results.append(f"✗ Node {i+1} ({node}): Connection failed - {str(e)}")
        
        all_ok = all("✓" in r for r in results)
        status_msg = "\n   ".join(results)
        
        return all_ok, f"Multi-node status:\n   {status_msg}"

