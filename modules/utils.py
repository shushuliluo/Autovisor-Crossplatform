import json
import os.path
import traceback
import platform
from typing import List, Optional, Union
from playwright.async_api import Page, Locator, TimeoutError
from modules.configs import Config
import time
from modules.logger import Logger

logger = Logger()

def save_cookies(cookies, filename="cookies.json"):
    """保存登录Cookies到文件"""
    with open(filename, 'w') as f:
        json.dump(cookies, f)

def load_cookies(filename="cookies.json"):
    """从文件加载 Cookies"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def bring_console_to_front():
    """跨平台的终端前置功能（仅Windows有效）"""
    if platform.system() == 'Windows':
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    else:
        # 其他平台可以添加相应实现或忽略
        pass

async def display_window(page: Page) -> None:
    """使用Playwright API显示窗口"""
    try:
        await page.bring_to_front()
        logger.info("播放窗口已自动前置.", shift=True)
    except Exception as e:
        logger.warn(f"窗口前置失败: {str(e)}")

async def hide_window(page: Page) -> None:
    """跨平台的窗口隐藏功能"""
    try:
        # 最小化窗口作为跨平台替代方案
        browser = page.context.browser
        if browser:
            await page.evaluate("window.moveTo(-3200, -3200);")
            logger.info("播放窗口已自动隐藏.")
    except Exception as e:
        logger.warn(f"窗口隐藏失败: {str(e)}")

async def get_browser_window(page: Page) -> Optional[Page]:
    """获取浏览器窗口对象（返回Page对象本身）"""
    try:
        await page.bring_to_front()
        return page
    except Exception:
        return None

async def evaluate_js(page: Page, wait_selector: Optional[str], js: str, 
                     timeout: Optional[float] = None, is_hike_class: bool = False) -> None:
    """跨平台的JS执行函数"""
    try:
        if wait_selector and not is_hike_class:
            await page.wait_for_selector(wait_selector, timeout=timeout)
        if not is_hike_class:
            await page.evaluate(js)
    except Exception as e:
        logger.write_log(f"Exec JS failed: {js} Selector:{wait_selector} Error:{repr(e)}\n")
        logger.write_log(traceback.format_exc())

async def evaluate_on_element(page: Page, selector: str, js: str, 
                             timeout: Optional[float] = None, is_hike_class: bool = False) -> None:
    """在元素上执行JS"""
    try:
        if selector and not is_hike_class:
            element = page.locator(selector).first
            await element.evaluate(js, timeout=timeout)
    except Exception as e:
        logger.write_log(f"Exec JS failed: Selector:{selector} JS:{js} Error:{repr(e)}\n")
        logger.write_log(traceback.format_exc())

async def optimize_page(page: Page, config: Config, is_new_version: bool = False, 
                       is_hike_class: bool = False) -> None:
    """页面优化函数（跨平台）"""
    try:
        await evaluate_js(page, ".studytime-div", config.pop_js, None, is_hike_class)
        if not is_new_version and not is_hike_class:
            hour = time.localtime().tm_hour
            if hour >= 18 or hour < 7:
                await evaluate_on_element(page, ".Patternbtn-div", "el=>el.click()", timeout=1500)
            await evaluate_on_element(page, ".exploreTip", "el=>el.remove()", timeout=1500)
            await evaluate_on_element(page, ".ai-helper-Index2", "el=>el.remove()", timeout=1500)
            await evaluate_on_element(page, ".aiMsg.once", "el=>el.remove()", timeout=1500)
            logger.info("页面优化完成!")
    except Exception as e:
        logger.write_log(f"Exec optimize_page failed. Error:{repr(e)}\n")
        logger.write_log(traceback.format_exc())

async def get_video_attr(page: Page, attr: str) -> any:
    """获取视频属性（跨平台）"""
    try:
        await page.wait_for_selector("video", state="attached", timeout=1000)
        return await page.evaluate(f'''document.querySelector('video').{attr}''')
    except Exception as e:
        logger.write_log(f"Exec get_video_attr failed. Error:{repr(e)}\n")
        logger.write_log(traceback.format_exc())
        return None

async def get_lesson_name(page: Page, is_hike_class: bool = False) -> str:
    """获取课程名称（跨平台）"""
    try:
        if is_hike_class:
            title_ele = await page.wait_for_selector("span")
            await page.wait_for_timeout(500)
            return await title_ele.get_attribute("title")
        else:
            title_ele = await page.wait_for_selector("#lessonOrder")
            await page.wait_for_timeout(500)
            return await title_ele.get_attribute("title")
    except Exception as e:
        logger.write_log(f"获取课程名称失败: {repr(e)}")
        return "未知课程"

async def get_filtered_class(page: Page, is_new_version: bool = False, 
                           is_hike_class: bool = False, include_all: bool = False) -> List[Locator]:
    """获取过滤后的课程列表（跨平台）"""
    try:
        if is_new_version:
            await page.wait_for_selector(".progress-num", timeout=2000)
        if is_hike_class:
            await page.wait_for_selector(".icon-finish", timeout=2000)
        else:
            await page.wait_for_selector(".time_icofinish", timeout=2000)
    except TimeoutError:
        pass

    if is_hike_class:
        all_class = await page.locator(".file-item").all()
        if include_all:
            return all_class
        else:
            return [each for each in all_class if not await each.locator(".icon-finish").count()]
    else:
        all_class = await page.locator(".clearfix.video").all()
        if include_all:
            return all_class
        else:
            to_learn_class = []
            for each in all_class:
                if is_new_version:
                    progress = await each.locator(".progress-num").text_content()
                    isDone = progress == "100%"
                else:
                    isDone = await each.locator(".time_icofinish").count()
                if not isDone:
                    to_learn_class.append(each)
            return to_learn_class