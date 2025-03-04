import sys
from pathlib import Path
from selenium.common.exceptions import WebDriverException

from sector_seek import find_assign_to
from chromedrivers import DriverHandler, log_into_mantis
from information_compile import generate_description_line, get_image, extract_asset_name, clean_debug_info


def upload_to_mantis(version, category, log_lines, project, username, password,
                     browser, path_to_asset=None, debug_info=None, web_driver=None, priority=None,
                     severity=None, late_image=None, prefix=None, rename_images=False, new_img_name=None):
    # Opens chrome browser, connects to mantis and uploads all of the gathered information
    # If priority is not None, it will treat the report as a batch report = will not as for image if its missing and
    #       will submit it automatically

    # region process information to insert in the form
    bug_descriptions = []
    images = []
    asset_info = ''

    if path_to_asset:
        asset_info = f"PATH TO ASSET: {path_to_asset}"
    if debug_info:
        debug_info = clean_debug_info(debug_info)
        asset_info += f"\n{debug_info}"
    if late_image:
        images.append(late_image)
    while len(log_lines) > 0:
        if ']' in log_lines:
            line_to_process = log_lines
        else:
            line_to_process = log_lines.popleft()

        bug_descriptions.append(generate_description_line(line_to_process))

        image_to_append = get_image(line_to_process)
        if image_to_append:
            if late_image:
                if Path(image_to_append) == Path(late_image):
                    continue
            else:
                images.append(image_to_append)
    # endregion

    driver = web_driver.get_driver()

    if not web_driver.is_active():
        driver = DriverHandler(browser=browser).get_driver()
        log_into_mantis(driver, username, password)

    # region Filling up the report form
    driver.get('https://qa.scssoft.com/login_select_proj_page.php?ref=bug_report_page.php')
    driver.find_element_by_xpath(f"//select[1]/option[text()='{project}']").click()
    driver.find_element_by_xpath("//input[@type='submit']").click()

    description_box = driver.find_element_by_xpath("//textarea[@class='form-control']")

    for p in range(len(bug_descriptions)):
        description_box.send_keys(bug_descriptions[p])
    if 'a' in category:
        description_box.send_keys('\n' + asset_info)

    first_bug_name = bug_descriptions[0].split(';')[0]
    summary = version
    if prefix and 'a' not in category:
        summary += f' - {prefix}'
    if 'a' in category and path_to_asset:
        asset_name = extract_asset_name(path_to_asset)
        summary += f' - {asset_name} - {first_bug_name}'
    else:
        summary += f' - {first_bug_name}'

    driver.find_element_by_xpath(f"//input[@name='summary']").send_keys(summary)

    assign_to = find_assign_to(f"{category}_{bug_descriptions[0]}", project[0])
    if assign_to != "":
        try:
            driver.find_element_by_xpath(f"//option[text()='{assign_to}']").click()
        except WebDriverException:
            try:
                assign_to = find_assign_to(f"{category}_{bug_descriptions[0]}", project[0], svn_not_found=True)
                driver.find_element_by_xpath(f"//option[text()='{assign_to}']").click()
            except WebDriverException:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                with open("./error_log.txt", "w", encoding='UTF-8') as error_log_file:
                    print("Writing error log")
                    error_log_file.write(f"An error occurred: ")
                    error_log_file.write(f"{exc_type} {exc_obj} {exc_tb}")

    driver.find_element_by_xpath(f"//option[text()='always']").click()

    if category == 'm':
        driver.find_element_by_xpath(f"//option[text()='map']").click()
    elif 'a' in category:
        driver.find_element_by_xpath(f"//option[text()='assets']").click()

    driver.find_element_by_xpath(f"//select[@name='priority']/option[text()='{priority}']").click()
    driver.find_element_by_xpath(f"//select[@name='severity']/option[text()='{severity}']").click()

    if rename_images:
        image_index = 0
        summary = summary.split(' - ')[1:]
        summary = ' - '.join(summary)
        summary = ' '.join(summary.split(' ')[:-1])
        dupl_index = 1
        for rename_me in images:
            images.remove(rename_me)
            old_extension = Path(rename_me).suffix
            directory = Path(rename_me).parent

            if new_img_name not in ['', 'Bug Summary (Default)']:
                summary = new_img_name
                summary = ' '.join(summary.split(' ')[:-1])

            if image_index > 0:
                summary = bug_descriptions[image_index].split(';')[0]
                summary = ' '.join(summary.split(' ')[:-1])
                if prefix:
                    summary = prefix + ' - ' + summary

            new_name = summary + old_extension
            rename_me = Path(rename_me)
            base_summary = summary

            while True:
                try:
                    rename_me = rename_me.rename(Path(directory, new_name))
                    images.insert(0, rename_me)
                    image_index += 1
                    break
                except FileExistsError:
                    summary = f'{base_summary} ({dupl_index})'
                    new_name = summary + old_extension
                    dupl_index += 1
                except FileNotFoundError:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    with open("./error_log.txt", "w", encoding='UTF-8') as error_log_file:
                        print("Writing error log")
                        error_log_file.write(f"An error occurred: ")
                        error_log_file.write(f"{exc_type} {exc_obj} {exc_tb}")

        images.reverse()
    for upload_me in images:
        driver.find_element_by_xpath("//input[@class='dz-hidden-input']").send_keys(str(upload_me))
    # endregion
