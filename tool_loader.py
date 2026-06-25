import importlib
import inspect
import os
import glob
import logging

log = logging.getLogger(__name__)


def load_tools(tools_dir: str = None) -> list:
    """
    Carrega automaticamente todas as *_tool.py de /tools/.
    Adicionar nova tool = criar o arquivo. Sem editar api.py.
    """
    if tools_dir is None:
        tools_dir = os.path.join(os.path.dirname(__file__), "tools")

    tools = []
    for filepath in sorted(glob.glob(os.path.join(tools_dir, "*_tool.py"))):
        module_name = f"tools.{os.path.basename(filepath)[:-3]}"
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                cls = getattr(module, attr_name)
                if (inspect.isclass(cls)
                        and cls.__module__ == module_name
                        and hasattr(cls, "name")
                        and hasattr(cls, "description")
                        and hasattr(cls, "run")):
                    tools.append(cls())
                    log.info("Tool carregada: %s", cls.name)
                    break
        except Exception as e:
            log.warning("Falha ao carregar %s: %s", module_name, e)

    return tools
