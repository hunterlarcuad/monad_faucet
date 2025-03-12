import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math

from DrissionPage import ChromiumOptions
from DrissionPage import Chromium
from DrissionPage._elements.none_element import NoneElement

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts
from fun_utils import time_difference
from fun_utils import seconds_to_hms

from conf import DEF_LOCAL_PORT
from conf import DEF_INCOGNITO
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS

from conf import DEF_CAPMONSTER_EXTENSION_PATH
from conf import EXTENSION_ID_CAPMONSTER
from conf import DEF_CAPMONSTER_KEY

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import logger

"""
2025.03.08
monad faucet
"""

DEF_URL_FAUCET = 'https://testnet.monad.xyz/'

# output
FIELD_NUM = 2
IDX_ACCOUNT = 0
IDX_UPDATE = -1

DEF_SUCCESS = 0
DEF_FAIL = -1
DEF_UNAVAILABLE = 10  # Service unavailable
DEF_CLAIMED = 10  # Claimed already


class FaucetTask():
    def __init__(self) -> None:
        self.args = None
        self.browser = None
        self.s_today = get_date(is_utc=True)
        self.file_proxy = None

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

    def __del__(self):
        self.status_save()

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == FIELD_NUM:
            try:
                s_val = int(lst_pre[idx_status])
            except: # noqa
                pass

        return s_val

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.browser:
                try:
                    self.browser.quit()
                except Exception as e: # noqa
                    # logger.info(f'[Close] Error: {e}')
                    pass

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        # Settings.singleton_tab_obj = True

        profile_path = s_profile

        # 是否设置无痕模式
        if DEF_INCOGNITO:
            co = ChromiumOptions().incognito(True)
        else:
            co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)
        # co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') # noqa

        # 设置不加载图片、静音
        co.no_imgs(True).mute(True)

        co.set_argument('--accept-lang', 'en-US')  # 设置语言为英语（美国）
        co.set_argument('--lang', 'en-US')

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        # 关闭沙盒模式
        # co.set_argument('--no-sandbox')

        # popups支持的取值
        # 0：允许所有弹窗
        # 1：只允许由用户操作触发的弹窗
        # 2：禁止所有弹窗
        # co.set_pref(arg='profile.default_content_settings.popups', value='0')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        self.load_extension(co, DEF_CAPMONSTER_EXTENSION_PATH)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        # co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa
        co.set_user_agent(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36') # noqa

        try:
            self.browser = Chromium(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

        # self.browser.wait.load_start()
        # tab.wait(2)

        self.init_capmonster()

    def load_extension(self, co, extersion_path):
        # 获取当前工作目录
        current_directory = os.getcwd()

        # 检查目录是否存在
        if os.path.exists(os.path.join(current_directory, extersion_path)): # noqa
            self.logit(None, f'okx plugin path: {extersion_path}')
            co.add_extension(extersion_path)
        else:
            self.logit(None, f'{extersion_path} plugin directory is not exist. Exit!') # noqa
            sys.exit(1)

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def init_capmonster(self):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        s_url = f'chrome-extension://{EXTENSION_ID_CAPMONSTER}/popup.html'
        tab = self.browser.latest_tab
        tab.get(s_url)
        # tab.wait.load_start()
        tab.wait(1)

        def get_balance():
            """
            Balance: $0.9987
            Balance: Wrong key
            """
            tab.wait(1)
            ele_info = tab.ele('tag:div@@class=sc-bdvvtL dTzMWc', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text
                logger.info(f'{s_info}')
                self.logit('init_capmonster', f'CapMonster {s_info}')
                if s_info.find('$') >= 0:
                    return True
                if s_info.find('Wrong key') >= 0:
                    return False
            return False

        def click_checkbox(s_value):
            ele_input = tab.ele(f'tag:input@@value={s_value}', timeout=2)
            if not isinstance(ele_input, NoneElement):
                if ele_input.states.is_checked is True:
                    ele_input.click(by_js=True)
                    self.logit(None, f'cancel checkbox {s_value}')
                    return True
            return False

        def cancel_checkbox():
            lst_text = [
                'ReCaptcha2',
                'ReCaptcha3',
                'ReCaptchaEnterprise',
                'GeeTest',
                'ImageToText',
                'BLS',
            ]
            for s_value in lst_text:
                click_checkbox(s_value)

        self.save_screenshot(name='capmonster_1.jpg')

        if get_balance():
            return True

        ele_block = tab.ele('tag:div@@class=sc-bdvvtL ehUtQX', timeout=2)
        if isinstance(ele_block, NoneElement):
            self.logit('init_capmonster', 'API-key block is not found')
            return False
        self.logit('init_capmonster', None)

        ele_input = ele_block.ele('tag:input')
        if not isinstance(ele_input, NoneElement):
            if ele_input.value == DEF_CAPMONSTER_KEY:
                self.logit(None, 'init_capmonster has been initialized before')
                return True
            if len(ele_input.value) > 0 and ele_input.value != DEF_CAPMONSTER_KEY: # noqa
                ele_input.click.multi(times=2)
                ele_input.clear(by_js=True)
                # tab.actions.type('BACKSPACE')
            tab.actions.move_to(ele_input).click().type(DEF_CAPMONSTER_KEY) # noqa
            tab.wait(1)
            ele_btn = ele_block.ele('tag:button')
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.states.is_enabled is False:
                    self.logit(None, 'The Save Button is_enabled=False')
                else:
                    ele_btn.click(by_js=True)
                    tab.wait(1)
                    self.logit(None, 'Saved capmonster_key [OK]')
                    cancel_checkbox()
                    if get_balance():
                        return True
            else:
                self.logit(None, 'the save button is not found')
                return False
        else:
            self.logit(None, 'the input element is not found')
            return False

        logger.info('capmonster init success')
        self.save_screenshot(name='capmonster_2.jpg')

    def save_screenshot(self, name):
        tab = self.browser.latest_tab
        # 对整页截图并保存
        # tab.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        tab.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def update_status(self, update_ts=None):
        # Maximum 1 request every 12 hours
        n_wait_sec = 12 * 3600

        if not update_ts:
            update_ts = time.time()
            update_ts += n_wait_sec

        # 随机增加一点时间
        add_ts = random.randint(300, 600)
        update_ts += add_ts
        update_time = format_ts(update_ts, 2, TZ_OFFSET)
        if self.args.s_profile in self.dic_status:
            self.dic_status[self.args.s_profile][1] = update_time
        else:
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
                update_time
            ]
        self.status_save()
        self.is_update = True

    def set_status(self, add_hour=2):
        """
        """
        avail_ts = time.time() + add_hour * 3600
        self.update_status(avail_ts)

    def get_tag_info(self, s_tag, s_text):
        """
        s_tag:
            span
            div
        """
        tab = self.browser.latest_tab
        s_path = f'@@tag()={s_tag}@@text():{s_text}'
        ele_info = tab.ele(s_path, timeout=1)
        if not isinstance(ele_info, NoneElement):
            # self.logit(None, f'[html] {s_text}: {ele_info.html}')
            s_info = ele_info.text.replace('\n', ' ')
            self.logit(None, f'[info][{s_tag}] {s_text}: {s_info}')
            return True
        return False

    def faucet_claim(self):
        """
        """
        tab = self.browser.latest_tab

        for i in range(1, DEF_NUM_TRY):
            self.logit('faucet_claim', f'Faucet Summit try_i={i}/{DEF_NUM_TRY}') # noqa

            tab.get(DEF_URL_FAUCET)
            # tab.wait.load_start()
            tab.wait(3)


            ele_btn = tab.ele('@@tag()=button@@role=checkbox@@aria-describedby=terms-description', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'checking the box of terms of service')
                ele_btn.click(by_js=True)
                tab.wait(1)

                ele_btn = tab.ele('@@tag()=button@@text()=Continue', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    self.logit(None, 'Click Continue Button')
                    ele_btn.click(by_js=True)
                    tab.wait(1)

            # Notice: The faucet is temporarily paused due to a surge of activity. Please try again soon. # noqa
            # Thanks for your patience.
            ele_div = tab.ele('@@tag()=div@@class:border-yellow-500@@text():Notice', timeout=2) # noqa
            if not isinstance(ele_div, NoneElement):
                tab.actions.move_to(ele_or_loc=ele_div)
                s_info = ele_div.text
                self.logit(None, f'faucet is unavailable. {s_info}')

                # Retry several hour later
                self.set_status(add_hour=3)
                self.is_update = False
                self.logit(None, 'Update status file.')

                return DEF_UNAVAILABLE

            # Verify you are human
            max_wait_sec = 30
            for i in range(max_wait_sec+1):
                if self.get_tag_info('span', 'Ready!'):
                    break
                self.logit(None, f'{i}/{max_wait_sec} Verify you are human ...') # noqa
                tab.wait(1)
                self.get_tag_info('span', 'In process')
                # auto_click()
            if i >= max_wait_sec:
                self.logit(None, f'{i}/{max_wait_sec} Verify Failed') # noqa
                tab.wait(3)
                continue

            # Claim Button
            for j in range(1, 10):
                button = tab.ele('@@tag()=button@@text()=Get Testnet MON', timeout=2) # noqa
                if button.states.is_enabled:
                    break
                n_sleep = j * 2
                self.logit(None, f'Wait Request button [sleep {n_sleep}]...')
                time.sleep(n_sleep)

            if button.states.is_enabled:
                s_key = self.dic_purse[self.args.s_profile][2]
                ele_input = tab.ele('@@tag()=input@@type=text', timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    self.logit(None, 'Enter wallet address ...')
                    tab.actions.move_to(ele_input).click().type(s_key) # noqa
                    tab.wait(1)

                if button.click(by_js=True):
                    self.logit(None, 'Click Request button ...')

                # Failed to send tokens
                # CloudFlare process failed
                # Sending tokens
                # Claimed already, Please try again later
                # Faucet is currently closed. Please try again later in a few hours # noqa
                # Drip successful
                # pdb.set_trace()
                i = 0
                max_wait_sec = 10
                s_info = ''
                while i < max_wait_sec:
                    tab.wait(1)
                    i += 1
                    ele_info = tab.ele('@@tag()=section@@aria-label:Notifications', timeout=1) # noqa
                    if not isinstance(ele_info, NoneElement):
                        s_info = ele_info.text.replace('\n', ' ')
                        self.logit(None, f'[info] {s_info}')

                        if s_info.find('Drip') >= 0:
                            self.update_status()
                            self.is_update = True
                            self.logit(None, 'Faucet Claim Success!')
                            return DEF_SUCCESS
                        elif s_info.find('Claimed already') >= 0:
                            self.set_status(add_hour=6)
                            self.is_update = False
                            return DEF_CLAIMED
                        elif s_info.find('Faucet is currently closed') >= 0:
                            # Retry one hour later
                            self.set_status(add_hour=3)
                            self.is_update = False
                            self.logit(None, 'Update status file.')
                            return DEF_UNAVAILABLE
                        elif s_info.find('Sending tokens') >= 0:
                            continue
                if i >= max_wait_sec:
                    self.logit(None, f'Fail to claim, took {i} seconds.') # noqa
                    continue
            else:
                tab.refresh()
                tab.wait.load_start()
                pass

        self.logit('faucet_claim', 'Claim finished!')
        self.close()
        return DEF_FAIL


def send_msg(instFaucetTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            if s_profile in instFaucetTask.dic_status:
                lst_status = instFaucetTask.dic_status[s_profile]
            else:
                lst_status = [s_profile, -1]

            s_info += '- {} {}\n'.format(
                s_profile,
                lst_status[1],
            )
        d_cont = {
            'title': 'Faucet Success! [monad_faucet]',
            'text': (
                'Faucet claim success [monad_faucet]\n'
                '- {}\n'
                '{}\n'
                .format(DEF_HEADER_STATUS, s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    instFaucetTask = FaucetTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(instFaucetTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    lst_wait = []
    # 将已完成的剔除掉
    instFaucetTask.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in instFaucetTask.dic_status:
            lst_status = instFaucetTask.dic_status[s_profile]
            if lst_status:
                avail_time = lst_status[1]
                if avail_time:

                    n_sec_wait = time_difference(avail_time) + 1
                    if n_sec_wait > 0:
                        lst_wait.append([s_profile, n_sec_wait])
                        # logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒') # noqa
                        n += 1
                        profiles.pop(i)
        else:
            continue
    logger.info('#'*40)
    if len(lst_wait) > 0:
        n_top = 5
        logger.info(f'***** Top {n_top} wait list')
        sorted_lst_wait = sorted(lst_wait, key=lambda x: x[1], reverse=False)
        for (s_profile, n_sec_wait) in sorted_lst_wait[:n_top]:
            logger.info(f'[{s_profile}] 还需等待{seconds_to_hms(n_sec_wait)}') # noqa
    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instFaucetTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            s_directory = f'{DEF_PATH_USER_DATA}/{args.s_profile}'
            if os.path.exists(s_directory) and os.path.isdir(s_directory):
                pass
            else:
                # Create new profile
                # instFaucetTask.initChrome(args.s_profile)
                # instFaucetTask.close()
                pass
            instFaucetTask.initChrome(args.s_profile)
            ret_claim = instFaucetTask.faucet_claim()
            return ret_claim

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                ret_claim = DEF_FAIL
                if j > 1:
                    logger.info(f'异常重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instFaucetTask.set_args(args)
                instFaucetTask.status_load()

                if s_profile in instFaucetTask.dic_status:
                    lst_status = instFaucetTask.dic_status[s_profile]
                else:
                    lst_status = None

                ret_claim = False
                is_ready_claim = True
                if lst_status:
                    avail_time = lst_status[1]

                    if avail_time:
                        n_sec_wait = time_difference(avail_time) + 1
                        if n_sec_wait > 0:
                            logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒') # noqa
                            is_ready_claim = False
                            break

                if is_ready_claim:
                    ret_claim = _run()

                if ret_claim == DEF_SUCCESS:
                    lst_success.append(s_profile)
                elif ret_claim in [DEF_SUCCESS, DEF_UNAVAILABLE, DEF_CLAIMED]:
                    instFaucetTask.close()
                    break
                elif ret_claim == DEF_FAIL:
                    continue
                else:
                    logger.info(f'[{s_profile}] Unknown ret_claim={ret_claim} [ERROR]') # noqa

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                instFaucetTask.close()
                if j < max_try_except:
                    time.sleep(5)

        if instFaucetTask.is_update is False:
            continue

        logger.info(f'[{s_profile}] Finish')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instFaucetTask, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
# noqa
python monad_faucet.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python monad_faucet.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=60
"""
